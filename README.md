# spotter-backend-assignment

### Assignment:
- Build an API that takes inputs of start and finish location both within the USA
- Return a map of the route along with optimal location to fuel up along the route -- optimal mostly means cost effective based on fuel prices
- Assume the vehicle has a maximum range of 500 miles so multiple fuel ups might need to be displayed on the route
- Also return the total money spent on fuel assuming the vehicle achieves 10 miles per gallon
- Use the attached file below for a list of fuel prices 
- Find a free API yourself for the map and routing

### Requirements:
- Build the app in latest stable Django
- Send your results for this project within 3 days of receiving the exercise
- The API should return results quickly, the quicker the better
- The API shouldn't need to call the free map/routing API you found too much. One call to the map/route API is ideal, two or three is acceptable
- Make a Loom where you use Postman or similar API platform to demonstrate the API working while also giving a quick overview of your code (5 minutes max)
- Share the Github code with us

## Solution

### Adopted Decisions
1. 'inputs of a start and finish location both within the USA', By this I assumed that the input will be a set of two coordinates (latitude and longitude) for the start and finish locations. To validate that both points are inside the contiguous USA, the API uses a bounding box (no external call needed). Any point that is inside the box but cannot be routed (for example, a point in the ocean) is rejected based on the error returned by the routing API, which the API handles and answers with a clear error message.
2. 'Return a map of the route along with optimal location to fuel up along the route', I decided that the map will be returned as a GeoJSON object, containing the route as a LineString and each fuel stop as a Point.
3. For this exercise I also assumed that the vehicle will start with a full tank of fuel, and that this initial fuel is not counted in the total cost.
4. The API that I found for routing is **OpenRouteService (ORS)**. It returns the route geometry and the total distance in a single call.
5. The CSV doesn't include coordinates, and its addresses are mostly highway exits (not street addresses), so they can't be reliably geocoded with an address geocoder. Instead, the stations are geocoded only once (offline) using the city/state centroid taken from a public US cities dataset (<SOURCE>) and stored in the database. This way no external call is needed per station. The tradeoff is precision: a city centroid can be several miles away from the real station, so some stations that are really near the route could be left out, and others could be included without being so close. This is a known limitation, and it is compensated in decision 7. Stations whose city/state can't be matched in the dataset are discarded.
6. If the CSV contains the same station (same ID) more than once with different prices, only the highest price is kept. I preferred a conservative approach, so the total cost is never underestimated.
7. Stations are only considered if they are within 10 miles of the route (the corridor distance), which is large enough to absorb part of the geocoding error. The detour to reach a station is not considered in the total cost, for the sake of completing this exercise in due time. Instead, the effective range is reduced to $500 - 2 \times \text{corridor distance} = 480$ miles. This way we know that we can always reach any station in range, even if we don't account for the extra fuel.

### Workflow
**First Setup (only once)**
1. Import the CSV, remove duplicates (keeping the highest price for each station ID), geocode each station with the city/state centroid and save it in the database.

**Per request**
1. The API will take the start and finish coordinates as input and validate them (bounding box).
2. The API will call the routing API once to get the route geometry and distance (converted to miles). If the routing API returns an error, the API handles it and responds with a clear message.
3. The API will select the stations inside the corridor (10 miles) and calculate the position of each one along the route (route mile).
4. The API will then calculate the optimal fuel stops, measuring the effective range (480 miles) along the route and keeping track of the fuel in the tank:
   1. Start at the start location with a full tank, treated as a station with price 0.
   2. If the finish location is within range, we stop here and buy only the fuel needed to reach it (if any).
   3. If there is a cheaper station than the current one within range, we go to the nearest one and buy only the fuel needed to reach it (if the fuel we already have is enough, we buy nothing).
   4. If there is none, we fill the tank in the current station and go to the cheapest station within range.
   5. Then we take that station as the new current station and repeat the process until we reach the finish location.
   6. If there is no station within range, the API returns an error.
5. The total cost of fuel is the sum of (gallons bought × price at that station), where gallons = miles / 10.
6. Once we reach the finish location, we will return the route geometry, the fuel stops (name, location, price and gallons bought) and the total cost of fuel.