import backend.main
app = backend.main.app

print(f"Total routes: {len(app.routes)}")
for r in app.routes:
    rtype = type(r).__name__
    path = getattr(r, "path", "no path")
    methods = getattr(r, "methods", set())
    print(f"  {rtype}: {methods} {path}")
