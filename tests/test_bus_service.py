from services.bus_service import get_all_buses


def test_get_all_buses():
    buses = get_all_buses()

    assert isinstance(buses, list)

    print("Bus retrieval successful!")
    print(f"Total buses: {len(buses)}")

    for bus in buses:
        print(bus)


if __name__ == "__main__":
    test_get_all_buses()