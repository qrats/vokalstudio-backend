from flask import make_response


def success_200(error=None):
    response = {'error': 'Request accepted' if error is None else error}
    return make_response(response, 200)


def success_201(error=None):
    response = {'error': 'Entity created' if error is None else error}
    return make_response(response, 201)


def success_204(error=None):
    response = {'error': 'Entity deleted' if error is None else error}
    return make_response(response, 204)


def error_400(error=None):
    response = {'error': 'Bad request' if error is None else error}
    return make_response(response, 400)


def error_401(error=None):
    response = {'error': 'Unauthorized' if error is None else error}
    return make_response(response, 401)


def error_403(error=None):
    response = {'error': 'Forbidden' if error is None else error}
    return make_response(response, 403)


def error_404(error=None):
    response = {'error': 'Entity not exist' if error is None else error}
    return make_response(response, 404)


def error_409(error=None):
    response = {'error': 'Conflict' if error is None else error}
    return make_response(response, 409)


def error_500(error=None):
    response = {'error': 'Internal server error' if error is None else error}
    return make_response(response, 500)
