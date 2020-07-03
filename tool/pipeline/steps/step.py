def register_pipeline_step():
    registry = {}

    def arg_wrapper(name=None):
        def registrar(cls):
            registry[name] = cls
            return cls

        return registrar

    arg_wrapper.all = registry
    return arg_wrapper

# Decorator for a build step
pipeline_step = register_pipeline_step()
