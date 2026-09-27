"""Optional browser runtime; desktop imports never load its dependencies."""
def create_app(main, **options):
    from .app import create_app as factory
    return factory(main, **options)


def mount_app(app, main, *, path="/ui", **options):
    child = create_app(main, **options)
    app.mount(path, child)
    return child


def run(main, *, host="127.0.0.1", port=8000, **options):
    import uvicorn
    uvicorn.run(create_app(main, **options), host=host, port=port)


__all__ = ["run", "create_app", "mount_app"]
