from app import create_app


def print_routes(app):
    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f"{rule.endpoint:30s}  [{methods:15s}]  {rule}")

if __name__ == '__main__':
    app = create_app()
    print_routes(app)