import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from routing.models import FuelStation


US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID',
    'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
    'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV',
    'WI', 'WY', 'DC',
}


def normalize_city(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    value = re.sub(r'\bst\.?\b', 'saint', value, flags=re.IGNORECASE)
    return ' '.join(value.casefold().split())


def load_cities(path):
    cities = defaultdict(list)
    with Path(path).open(encoding='utf-8') as handle:
        for line in handle:
            fields = line.rstrip('\n').split('\t')
            if len(fields) < 15:
                continue
            state = fields[10].upper()
            if state in US_STATES:
                try:
                    population = int(fields[14] or 0)
                    lat, lng = float(fields[4]), float(fields[5])
                except ValueError:
                    continue
                cities[(normalize_city(fields[1]), state)].append(
                    (population, lat, lng)
                )
    return {key: max(values) for key, values in cities.items()}


class Command(BaseCommand):
    help = 'Import and geocode fuel stations from a CSV using city centroids.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path')
        parser.add_argument('cities_path')

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path'])
        cities = load_cities(options['cities_path'])
        if not csv_path.exists():
            raise CommandError(f'CSV file not found: {csv_path}')
        with csv_path.open(newline='', encoding='utf-8-sig') as handle:
            sample = handle.read(8192)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',\t')
            except csv.Error as exc:
                raise CommandError('Could not detect CSV delimiter.') from exc
            reader = csv.DictReader(handle, dialect=dialect)
            required = {'OPIS Truckstop ID', 'Truckstop Name', 'Address', 'City', 'State', 'Retail Price'}
            if not required.issubset(reader.fieldnames or []):
                raise CommandError('CSV is missing required headers.')
            rows = list(reader)

        deduped = {}
        duplicate_count = 0
        invalid_price = 0
        non_us = 0
        for row in rows:
            state = row['State'].strip().upper()
            if state not in US_STATES:
                non_us += 1
                continue
            try:
                price = float(row['Retail Price'])
            except (TypeError, ValueError):
                invalid_price += 1
                continue
            key = row['OPIS Truckstop ID'].strip()
            candidate = (price, row)
            if key in deduped:
                duplicate_count += 1
                if price > deduped[key][0]:
                    deduped[key] = candidate
            else:
                deduped[key] = candidate

        unmatched = []
        stations = []
        for opis_id, (price, row) in deduped.items():
            state = row['State'].strip().upper()
            centroid = cities.get((normalize_city(row['City']), state))
            if centroid is None:
                unmatched.append(f"{row['City'].strip()}, {state}")
                continue
            _, lat, lng = centroid
            stations.append(FuelStation(
                opis_id=opis_id,
                name=row['Truckstop Name'].strip(),
                address=row['Address'].strip(),
                city=' '.join(row['City'].split()),
                state=state,
                price=price,
                lat=lat,
                lng=lng,
            ))

        with transaction.atomic():
            FuelStation.objects.all().delete()
            FuelStation.objects.bulk_create(stations, batch_size=1000)

        self.stdout.write(
            f'rows read: {len(rows)}; duplicates merged: {duplicate_count}; '
            f'matched: {len(stations)}; unmatched: {len(unmatched)}; '
            f'non-U.S. skipped: {non_us}; invalid price skipped: {invalid_price}'
        )
        if len(stations) < 100:
            self.stdout.write(self.style.WARNING(
                'WARNING: fewer than 100 stations matched. '
                'Check that the cities dataset is the complete GeoNames US.txt file.'
            ))
        if unmatched:
            self.stdout.write('unmatched examples: ' + '; '.join(unmatched[:5]))
