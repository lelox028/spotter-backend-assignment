# spotter-bakend-assignment

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
1. 'inputs of a start and finish location both within the USA', By this I assumed that the input will be a set of two coordinates (latitude and longitude) for the start and finish locations. 
2. 'Return a map of the route along with optimal location to fuel up along the route', I decided that the map will be returned as a GEOJSON object.
3. For this excercise i also assumed that the vehicle will start with a full tank of fuel.
4. The API that i found for routing is 
   
### Workflow
1. The API will take the start and finish coordinates as input.
2. The API will call the routing API to get the routes geometry and distance.
3. The API will then calculate the optimal fuel stops based on the distance and fuel prices.
   1. First we need to find the chepeast fuel station within the range of the vehicle (500 miles) and inside a certain distance from the route and from the start location.
   2. Then we will take the current station as the new start location and repeat the process until we reach the finish location.
   3. Whenever we reach a fuel station, we will calculate the total cost of fuel based on the distance traveled and the fuel price at that station, and in each station we will only refuel the amount of fuel needed to reach the next (cheapest) station or the finish location.
4. Once we reach the finish location, we will return the route geometry, the fuel stops and the total cost of fuel.