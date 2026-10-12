from services.route_service import get_all_routes


def test_route_service():
    routes = get_all_routes()

    print(f"Routes found: {len(routes)}")
    for route in routes:
        print(route)


if __name__ == "__main__":
    test_route_service()
