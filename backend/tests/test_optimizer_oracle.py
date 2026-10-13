"""Independent integer-fuel dynamic-programming oracle for the greedy solver."""
import random
from decimal import Decimal as D
import pytest
from apps.routes.services.domain import Candidate,PlanningError
from apps.routes.services.optimizer import optimize_fuel


def exact_cost(positions, prices, destination, initial):
    states={initial:D(0)}; previous=0
    for position,price in zip(positions,prices):
        arrivals={fuel-(position-previous):cost for fuel,cost in states.items() if fuel>=position-previous}
        states={}
        for arrival,cost in arrivals.items():
            for departure in range(arrival,51):
                candidate=cost+(departure-arrival)*D(price)
                states[departure]=min(states.get(departure,D("Infinity")),candidate)
        previous=position
    costs=[cost for fuel,cost in states.items() if fuel>=destination-previous]
    return min(costs) if costs else None


def test_greedy_matches_exact_oracle_on_generated_routes():
    randomizer=random.Random(812)
    for _ in range(60):
        positions=sorted(randomizer.sample(range(1,140),randomizer.randint(1,6)))
        prices=[randomizer.randint(1,7) for _ in positions]
        initial=randomizer.randint(1,50)
        destination=positions[-1]+randomizer.randint(1,50)
        reference=exact_cost(positions,prices,destination,initial)
        candidates=[Candidate(i,D(position*10),D(price)) for i,(position,price) in enumerate(zip(positions,prices),start=1)]
        if reference is None:
            with pytest.raises(PlanningError):optimize_fuel(destination*10,candidates,initial_gallons=initial)
        else:
            assert optimize_fuel(destination*10,candidates,initial_gallons=initial).total_cost==reference
