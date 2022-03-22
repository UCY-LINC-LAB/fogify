import json

class Cache(object):

    @staticmethod
    def put(key, value, value_to_json=True):
        from agent.models import Status
        if value_to_json:
            Status.update_config(name=key, value=json.dumps(value))
            return
        Status.update_config(name=key, value=value)
    @staticmethod
    def get(key, value_from_json=True):
        from agent.models import Status
        res = Status.query.filter_by(name=key).first()
        if not res: return None
        if value_from_json:
            return json.loads(res.value)
        return res.value

    @staticmethod
    def memoize(func):
        def memoized_func(*args):
            function_name = func.__name__
            str_args = ",".join([str(arg) for arg in args])
            key = f"{function_name}|{str_args}"
            res = Cache.get(key)
            if res: return res
            result = func(*args)
            Cache.put(key, result)
            return result
        return memoized_func

    @staticmethod
    def clean_up():
        from agent.models import Status
        Status.remove_all()
