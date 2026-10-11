from services.route_service import get_all_routes, add_route


def test_route_service():
    routes = get_all_routes()

    print(f"Routes before: {len(routes)}")

    new_route = add_route(
        name="Kitwe - Ndola",
        description="Intercity route"
    )

    print("Created route:", new_route)

    routes = get_all_routes()

    print(f"Routes after: {len(routes)}")


if __name__ == "__main__":
    test_route_service()