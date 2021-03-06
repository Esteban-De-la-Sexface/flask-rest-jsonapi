# -*- coding: utf-8 -*-

from six.moves.urllib.parse import urlencode
import pytest
import json

from sqlalchemy import create_engine, Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from flask import Blueprint, make_response
from marshmallow_jsonapi.flask import Schema, Relationship
from marshmallow_jsonapi import fields

from flask_rest_jsonapi import Api, ResourceList, ResourceDetail, ResourceRelationship, JsonApiException
from flask_rest_jsonapi.querystring import QueryStringManager as QSManager
from flask_rest_jsonapi.data_layers.alchemy import SqlalchemyDataLayer
from flask_rest_jsonapi.data_layers.base import BaseDataLayer


@pytest.fixture(scope="module")
def base():
    yield declarative_base()


@pytest.fixture(scope="module")
def person_model(base):
    class Person(base):

        __tablename__ = 'person'

        person_id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False)
        birth_date = Column(DateTime)
        computers = relationship("Computer", backref="owner")
    yield Person


@pytest.fixture(scope="module")
def computer_model(base):
    class Computer(base):

        __tablename__ = 'computer'

        id = Column(Integer, primary_key=True)
        serial = Column(String, nullable=False)
        person_id = Column(Integer, ForeignKey('person.person_id'))
    yield Computer


@pytest.fixture(scope="module")
def engine(person_model, computer_model):
    engine = create_engine("sqlite:///:memory:")
    person_model.metadata.create_all(engine)
    computer_model.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture()
def person(session, person_model):
    person_ = person_model(name='test')
    session_ = session
    session_.add(person_)
    session_.commit()
    yield person_
    session_.delete(person_)
    session_.commit()


@pytest.fixture()
def person_2(session, person_model):
    person_ = person_model(name='test2')
    session_ = session
    session_.add(person_)
    session_.commit()
    yield person_
    session_.delete(person_)
    session_.commit()


@pytest.fixture()
def computer(session, computer_model):
    computer_ = computer_model(serial='1')
    session_ = session
    session_.add(computer_)
    session_.commit()
    yield computer_
    session_.delete(computer_)
    session_.commit()


@pytest.fixture(scope="module")
def dummy_decorator():
    def deco(f):
        def wrapper_f(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper_f
    yield deco


@pytest.fixture(scope="module")
def person_schema():
    class PersonSchema(Schema):
        class Meta:
            type_ = 'person'
            self_view = 'api.person_detail'
            self_view_kwargs = {'person_id': '<id>'}
        id = fields.Str(dump_only=True, attribute='person_id')
        name = fields.Str(required=True)
        birth_date = fields.DateTime()
        computers = Relationship(related_view='api.computer_list',
                                 related_view_kwargs={'person_id': '<person_id>'},
                                 schema='ComputerSchema',
                                 type_='computer',
                                 many=True)
    yield PersonSchema


@pytest.fixture(scope="module")
def computer_schema():
    class ComputerSchema(Schema):
        class Meta:
            type_ = 'computer'
            self_view = 'api.computer_detail'
            self_view_kwargs = {'id': '<id>'}
        id = fields.Str(dump_only=True)
        serial = fields.Str(required=True)
        owner = Relationship(related_view='api.person_detail',
                             related_view_kwargs={'person_id': '<owner.person_id>'},
                             schema='PersonSchema',
                             id_field='person_id',
                             type_='person')
    yield ComputerSchema


def before_create_object_(self, data, **view_kwargs):
    pass


def before_update_object_(self, obj, data, **view_kwargs):
    pass


def before_delete_object_(self, obj, **view_kwargs):
    pass


@pytest.fixture(scope="module")
def person_list(session, person_model, dummy_decorator, person_schema):
    class PersonList(ResourceList):
        schema = person_schema
        data_layer_kwargs = {'model': person_model, 'session': session}

        class Meta:
            data_layer = SqlalchemyDataLayer
            get_decorators = [dummy_decorator]
            post_decorators = [dummy_decorator]
            before_create_object = before_create_object_
            get_schema_kwargs = dict()
            post_schema_kwargs = dict()
    yield PersonList


@pytest.fixture(scope="module")
def person_detail(session, person_model, dummy_decorator, person_schema):
    class PersonDetail(ResourceDetail):
        schema = person_schema
        data_layer_kwargs = {'model': person_model,
                             'session': session,
                             'url_field': 'person_id'}

        class Meta:
            get_decorators = [dummy_decorator]
            patch_decorators = [dummy_decorator]
            delete_decorators = [dummy_decorator]
            before_update_object = before_update_object_
            before_delete_object = before_delete_object_
            get_schema_kwargs = dict()
            patch_schema_kwargs = dict()
            delete_schema_kwargs = dict()
    yield PersonDetail


@pytest.fixture(scope="module")
def person_computers(session, person_model, dummy_decorator, person_schema):
    class PersonComputersRelationship(ResourceRelationship):
        schema = person_schema
        data_layer_kwargs = {'session': session,
                             'model': person_model,
                             'url_field': 'person_id'}

        class Meta:
            get_decorators = [dummy_decorator]
            post_decorators = [dummy_decorator]
            patch_decorators = [dummy_decorator]
            delete_decorators = [dummy_decorator]
            relationship_mapping = {'computers': {'relationship_field': 'computers', 'id_field': 'id'}}
    yield PersonComputersRelationship


@pytest.fixture(scope="module")
def person_list_raise_jsonapiexception():
    class PersonList(ResourceList):
        def get(self):
            raise JsonApiException('', '')
    yield PersonList


@pytest.fixture(scope="module")
def person_list_raise_exception():
    class PersonList(ResourceList):
        def get(self):
            raise Exception()
    yield PersonList


@pytest.fixture(scope="module")
def person_list_response():
    class PersonList(ResourceList):
        def get(self):
            return make_response('')
    yield PersonList


@pytest.fixture(scope="module")
def person_list_without_schema(session, person_model):
    class PersonList(ResourceList):
        data_layer_kwargs = {'model': person_model, 'session': session}

        def get(self):
            return make_response('')
    yield PersonList


def query_(self, **view_kwargs):
    if view_kwargs.get('person_id') is not None:
        return self.session.query(computer_model).join(person_model).filter_by(person_id=view_kwargs['person_id'])
    return self.session.query(computer_model)


@pytest.fixture(scope="module")
def computer_list(session, computer_model, computer_schema):
    class ComputerList(ResourceList):
        schema = computer_schema
        data_layer_kwargs = {'model': computer_model, 'session': session}

        class Meta:
            query = query_
            relationship_mapping = {'person': {'relationship_field': 'owner', 'id_field': 'person_id'}}
    yield ComputerList


@pytest.fixture(scope="module")
def computer_detail(session, computer_model, dummy_decorator, computer_schema):
    class ComputerDetail(ResourceDetail):
        schema = computer_schema
        data_layer_kwargs = {'model': computer_model,
                             'session': session}

        class Meta:
            not_allowed_methods = ['DELETE']
    yield ComputerDetail


@pytest.fixture(scope="module")
def computer_owner(session, computer_model, dummy_decorator, computer_schema):
    class ComputerOwnerRelationship(ResourceRelationship):
        schema = computer_schema
        data_layer_kwargs = {'session': session,
                             'model': computer_model}
    yield ComputerOwnerRelationship


@pytest.fixture(scope="module")
def api_blueprint(client):
    bp = Blueprint('api', __name__)
    yield bp


@pytest.fixture(scope="module")
def register_routes(client, app, api_blueprint, person_list, person_detail, person_computers,
                    person_list_raise_jsonapiexception, person_list_raise_exception, person_list_response,
                    person_list_without_schema, computer_list, computer_detail, computer_owner):
    api = Api(api_blueprint)
    api.route(person_list, 'person_list', '/persons')
    api.route(person_detail, 'person_detail', '/persons/<int:person_id>')
    api.route(person_computers, 'person_computers', '/persons/<int:person_id>/relationships/computers')
    api.route(person_computers, 'person_computers_error', '/persons/<int:person_id>/relationships/computer')
    api.route(person_list_raise_jsonapiexception, 'person_list_jsonapiexception', '/persons_jsonapiexception')
    api.route(person_list_raise_exception, 'person_list_exception', '/persons_exception')
    api.route(person_list_response, 'person_list_response', '/persons_response')
    api.route(person_list_without_schema, 'person_list_without_schema', '/persons_without_schema')
    api.route(computer_list, 'computer_list', '/computers', '/persons/<int:person_id>/computers')
    api.route(computer_list, 'computer_detail', '/computers/<int:id>')
    api.route(computer_owner, 'computer_owner', '/computers/<int:id>/relationships/owner')
    api.init_app(app)


# test good cases
def test_get_list(client, register_routes, person, person_2):
    with client:
        querystring = urlencode({'page[number]': 1,
                                 'page[size]': 1,
                                 'fields[person]': 'name,birth_date',
                                 'sort': '-name',
                                 'include': 'computers.owner',
                                 'filters': json.dumps(
                                     [
                                         {
                                             'and': [
                                                 {
                                                     'name': 'computers',
                                                     'op': 'any',
                                                     'val': {
                                                         'name': 'serial',
                                                         'op': 'eq',
                                                         'val': '0000'
                                                     }
                                                 },
                                                 {
                                                     'or': [
                                                         {
                                                             'name': 'name',
                                                             'op': 'like',
                                                             'val': '%test%'
                                                         },
                                                         {
                                                             'name': 'name',
                                                             'op': 'like',
                                                             'val': '%test2%'
                                                         }
                                                     ]
                                                 }
                                             ]
                                         }
                                     ])})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_get_list_disable_pagination(client, register_routes):
    with client:
        querystring = urlencode({'page[size]': 0})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_head_list(client, register_routes):
    with client:
        response = client.head('/persons', content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_post_list(client, register_routes, computer):
    payload = {
        'data': {
            'type': 'person',
            'attributes': {
                'name': 'test'
            },
            'relationships': {
                'computers': {
                    'data': [
                        {
                            'type': 'computer',
                            'id': str(computer.id)
                        }
                    ]
                }
            }
        }
    }

    with client:
        response = client.post('/persons', data=json.dumps(payload), content_type='application/vnd.api+json')
        assert response.status_code == 201


def test_post_list_single(client, register_routes, person):
    payload = {
        'data': {
            'type': 'computer',
            'attributes': {
                'serial': '1'
            },
            'relationships': {
                'owner': {
                    'data': {
                        'type': 'person',
                        'id': str(person.person_id)
                    }
                }
            }
        }
    }

    with client:
        response = client.post('/computers', data=json.dumps(payload), content_type='application/vnd.api+json')
        assert response.status_code == 201


def test_get_detail(client, register_routes, person):
    with client:
        response = client.get('/persons/' + str(person.person_id), content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_patch_detail(client, register_routes, computer, person):
    payload = {
        'data': {
            'id': str(person.person_id),
            'type': 'person',
            'attributes': {
                'name': 'test2'
            },
            'relationships': {
                'computers': {
                    'data': [
                        {
                            'type': 'computer',
                            'id': str(computer.id)
                        }
                    ]
                }
            }
        }
    }

    with client:
        response = client.patch('/persons/' + str(person.person_id),
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_delete_detail(client, register_routes, person):
    with client:
        response = client.delete('/persons/' + str(person.person_id), content_type='application/vnd.api+json')
        assert response.status_code == 204


def test_get_relationship(session, client, register_routes, computer, person):
    session_ = session
    person.computers = [computer]
    session_.commit()

    with client:
        response = client.get('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                              content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_get_relationship_empty(client, register_routes, person):
    with client:
        response = client.get('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                              content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_get_relationship_single(session, client, register_routes, computer, person):
    session_ = session
    computer.owner = person
    session_.commit()

    with client:
        response = client.get('/computers/' + str(computer.id) + '/relationships/owner',
                              content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_get_relationship_single_empty(session, client, register_routes, computer):
    with client:
        response = client.get('/computers/' + str(computer.id) + '/relationships/owner',
                              content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_post_relationship(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'type': 'computer',
                'id': str(computer.id)
            }
        ]
    }

    with client:
        response = client.post('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                               data=json.dumps(payload),
                               content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_post_relationship_not_list(client, register_routes, computer, person):
    payload = {
        'data': {
            'type': 'person',
            'id': str(person.person_id)
        }
    }

    with client:
        response = client.post('/computers/' + str(computer.id) + '/relationships/owner',
                               data=json.dumps(payload),
                               content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_patch_relationship(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'type': 'computer',
                'id': str(computer.id)
            }
        ]
    }

    with client:
        response = client.patch('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_patch_relationship_single(client, register_routes, computer, person):
    payload = {
        'data': {
            'type': 'person',
            'id': str(person.person_id)
        }
    }
    with client:
        response = client.patch('/computers/' + str(computer.id) + '/relationships/owner',
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_delete_relationship(session, client, register_routes, computer, person):
    session_ = session
    person.computers = [computer]
    session_.commit()

    payload = {
        'data': [
            {
                'type': 'computer',
                'id': str(computer.id)
            }
        ]
    }

    with client:
        response = client.delete('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                 data=json.dumps(payload),
                                 content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_delete_relationship_single(session, client, register_routes, computer, person):
    session_ = session
    computer.owner = person
    session_.commit()

    payload = {
        'data': {
            'type': 'person',
            'id': str(person.person_id)
        }
    }

    with client:
        response = client.delete('/computers/' + str(computer.id) + '/relationships/owner',
                                 data=json.dumps(payload),
                                 content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_get_list_response(client, register_routes):
    with client:
        response = client.get('/persons_response', content_type='application/vnd.api+json')
        assert response.status_code == 200


# test errors
def test_wrong_content_type(client, register_routes):
    with client:
        response = client.get('/persons')
        assert response.status_code == 415


def test_wrong_accept_header(client, register_routes):
    with client:
        response = client.get('/persons', content_type='application/vnd.api+json', headers={'Accept': 'error'})
        assert response.status_code == 406


@pytest.fixture(scope="module")
def wrong_data_layer():
    class WrongDataLayer(object):
        pass
    yield WrongDataLayer


def test_wrong_data_layer_inheritence(wrong_data_layer):
    with pytest.raises(Exception):
        class PersonDetail(ResourceDetail):
            class Meta:
                data_layer = wrong_data_layer


def test_wrong_data_layer_kwargs_type():
    with pytest.raises(Exception):
        class PersonDetail(ResourceDetail):
            data_layer_kwargs = list()


def test_get_list_jsonapiexception(client, register_routes):
    with client:
        response = client.get('/persons_jsonapiexception', content_type='application/vnd.api+json')
        assert response.status_code == 500


def test_get_list_exception(client, register_routes):
    with client:
        response = client.get('/persons_exception', content_type='application/vnd.api+json')
        assert response.status_code == 500


def test_get_list_without_data_layer(client, register_routes):
    with client:
        response = client.post('/persons_without_schema', content_type='application/vnd.api+json')
        assert response.status_code == 500


def test_get_list_bad_request(client, register_routes):
    with client:
        querystring = urlencode({'page[number': 3})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_invalid_fields(client, register_routes):
    with client:
        querystring = urlencode({'fields[person]': 'error'})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_invalid_include(client, register_routes):
    with client:
        querystring = urlencode({'include': 'error'})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_invalid_filters(client, register_routes):
    with client:
        querystring = urlencode({'filters': json.dumps({})})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_invalid_filters_parsing(client, register_routes):
    with client:
        querystring = urlencode({'filters': 'error'})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_invalid_page(client, register_routes):
    with client:
        querystring = urlencode({'page[number]': 'error'})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_invalid_sort(client, register_routes):
    with client:
        querystring = urlencode({'sort': 'error'})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_detail_object_not_found(client, register_routes):
    with client:
        response = client.get('/persons/3', content_type='application/vnd.api+json')
        assert response.status_code == 404


def test_post_relationship_related_object_not_found(client, register_routes, person):
    payload = {
        'data': [
            {
                'type': 'computer',
                'id': '2'
            }
        ]
    }

    with client:
        response = client.post('/persons/' + str(person.person_id) + '/relationships/computers',
                               data=json.dumps(payload),
                               content_type='application/vnd.api+json')
        assert response.status_code == 404


def test_get_relationship_relationship_field_not_found(client, register_routes, person):
    with client:
        response = client.get('/persons/' + str(person.person_id) + '/relationships/computer',
                              content_type='application/vnd.api+json')
        assert response.status_code == 500


@pytest.fixture(scope="module")
def full_not_implemented_data_layer():
    class FullNotImplementedDataLayer(BaseDataLayer):
        pass
    yield FullNotImplementedDataLayer


def test_not_implemented_data_layer(session, person_model, full_not_implemented_data_layer):
    with pytest.raises(NotImplementedError):
        class PersonList(ResourceList):
            data_layer_kwargs = {'session': session, 'model': person_model}

            class Meta:
                data_layer = full_not_implemented_data_layer


def test_api(app, person_list):
    api = Api(app)
    api.route(person_list, 'person_list', '/persons', '/person_list')
    api.init_app()


def test_api_resources(app, person_list):
    api = Api()
    api.route(person_list, 'person_list', '/persons', '/person_list')
    api.init_app(app)


def test_get_list_invalid_filters_val(client, register_routes):
    with client:
        querystring = urlencode({'filters': json.dumps([{'name': 'computers', 'op': 'any'}])})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_name(client, register_routes):
    with client:
        querystring = urlencode({'filters': json.dumps([{'name': 'computers__serial', 'op': 'any', 'val': '1'}])})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 200


def test_get_list_no_name(client, register_routes):
    with client:
        querystring = urlencode({'filters': json.dumps([{'op': 'any', 'val': '1'}])})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_no_op(client, register_routes):
    with client:
        querystring = urlencode({'filters': json.dumps([{'name': 'computers__serial', 'val': '1'}])})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_attr_error(client, register_routes):
    with client:
        querystring = urlencode({'filters': json.dumps([{'name': 'error', 'op': 'eq', 'val': '1'}])})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_get_list_field_error(client, register_routes):
    with client:
        querystring = urlencode({'filters': json.dumps([{'name': 'name', 'op': 'eq', 'field': 'error'}])})
        response = client.get('/persons' + '?' + querystring, content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_sqlalchemy_data_layer_without_session(person_model, person_list):
    with pytest.raises(Exception):
        SqlalchemyDataLayer(model=person_model, resource=person_list)


def test_sqlalchemy_data_layer_without_model(session, person_list):
    with pytest.raises(Exception):
        SqlalchemyDataLayer(session=session, resource=person_list)


def test_sqlalchemy_data_layer_get_object_error(session, person_model):
    with pytest.raises(Exception):
        dl = SqlalchemyDataLayer(session=session, model=person_model, id_field='error')
        dl.get_object(**dict())


def test_sqlalchemy_data_layer_create_relationship_field_not_found(session, person_model):
    with pytest.raises(Exception):
        dl = SqlalchemyDataLayer(session=session, model=person_model)
        dl.create_relationship(dict(), 'error', '', **{'id': 1})


def test_sqlalchemy_data_layer_get_relationship_field_not_found(session, person_model):
    with pytest.raises(Exception):
        dl = SqlalchemyDataLayer(session=session, model=person_model)
        dl.get_relationship('error', '', '', **{'id': 1})


def test_sqlalchemy_data_layer_update_relationship_field_not_found(session, person_model):
    with pytest.raises(Exception):
        dl = SqlalchemyDataLayer(session=session, model=person_model)
        dl.update_relationship(dict(), 'error', '', **{'id': 1})


def test_sqlalchemy_data_layer_delete_relationship_field_not_found(session, person_model):
    with pytest.raises(Exception):
        dl = SqlalchemyDataLayer(session=session, model=person_model)
        dl.delete_relationship(dict(), 'error', '', **{'id': 1})


def test_post_list_incorrect_type(client, register_routes, computer):
    payload = {
        'data': {
            'type': 'error',
            'attributes': {
                'name': 'test'
            },
            'relationships': {
                'computers': {
                    'data': [
                        {
                            'type': 'computer',
                            'id': str(computer.id)
                        }
                    ]
                }
            }
        }
    }

    with client:
        response = client.post('/persons', data=json.dumps(payload), content_type='application/vnd.api+json')
        assert response.status_code == 409


def test_post_list_validation_error(client, register_routes, computer):
    payload = {
        'data': {
            'type': 'person',
            'attributes': {},
            'relationships': {
                'computers': {
                    'data': [
                        {
                            'type': 'computer',
                            'id': str(computer.id)
                        }
                    ]
                }
            }
        }
    }

    with client:
        response = client.post('/persons', data=json.dumps(payload), content_type='application/vnd.api+json')
        assert response.status_code == 422


def test_patch_detail_incorrect_type(client, register_routes, computer, person):
    payload = {
        'data': {
            'id': str(person.person_id),
            'type': 'error',
            'attributes': {
                'name': 'test2'
            },
            'relationships': {
                'computers': {
                    'data': [
                        {
                            'type': 'computer',
                            'id': str(computer.id)
                        }
                    ]
                }
            }
        }
    }

    with client:
        response = client.patch('/persons/' + str(person.person_id),
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 409


def test_patch_detail_validation_error(client, register_routes, computer, person):
    payload = {
        'data': {
            'id': str(person.person_id),
            'type': 'person',
            'attributes': {
                'name': {'test2': 'error'}
            },
            'relationships': {
                'computers': {
                    'data': [
                        {
                            'type': 'computer',
                            'id': str(computer.id)
                        }
                    ]
                }
            }
        }
    }

    with client:
        response = client.patch('/persons/' + str(person.person_id),
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 422


def test_patch_detail_missing_id(client, register_routes, computer, person):
    payload = {
        'data': {
            'type': 'person',
            'attributes': {
                'name': 'test2'
            },
            'relationships': {
                'computers': {
                    'data': [
                        {
                            'type': 'computer',
                            'id': str(computer.id)
                        }
                    ]
                }
            }
        }
    }

    with client:
        response = client.patch('/persons/' + str(person.person_id),
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_patch_detail_wrong_id(client, register_routes, computer, person):
    payload = {
        'data': {
            'id': 'error',
            'type': 'person',
            'attributes': {
                'name': 'test2'
            },
            'relationships': {
                'computers': {
                    'data': [
                        {
                            'type': 'computer',
                            'id': str(computer.id)
                        }
                    ]
                }
            }
        }
    }

    with client:
        response = client.patch('/persons/' + str(person.person_id),
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_post_relationship_no_data(client, register_routes, computer, person):
    with client:
        response = client.post('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                               data=json.dumps(dict()),
                               content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_post_relationship_not_list_missing_type(client, register_routes, computer, person):
    payload = {
        'data': {
            'id': str(person.person_id)
        }
    }

    with client:
        response = client.post('/computers/' + str(computer.id) + '/relationships/owner',
                               data=json.dumps(payload),
                               content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_post_relationship_not_list_missing_id(client, register_routes, computer, person):
    payload = {
        'data': {
            'type': 'person'
        }
    }

    with client:
        response = client.post('/computers/' + str(computer.id) + '/relationships/owner',
                               data=json.dumps(payload),
                               content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_post_relationship_not_list_wrong_type(client, register_routes, computer, person):
    payload = {
        'data': {
            'type': 'error',
            'id': str(person.person_id)
        }
    }

    with client:
        response = client.post('/computers/' + str(computer.id) + '/relationships/owner',
                               data=json.dumps(payload),
                               content_type='application/vnd.api+json')
        assert response.status_code == 409


def test_post_relationship_missing_type(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'id': str(computer.id)
            }
        ]
    }

    with client:
        response = client.post('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                               data=json.dumps(payload),
                               content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_post_relationship_missing_id(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'type': 'computer',
            }
        ]
    }

    with client:
        response = client.post('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                               data=json.dumps(payload),
                               content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_post_relationship_wrong_type(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'type': 'error',
                'id': str(computer.id)
            }
        ]
    }

    with client:
        response = client.post('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                               data=json.dumps(payload),
                               content_type='application/vnd.api+json')
        assert response.status_code == 409


def test_patch_relationship_no_data(client, register_routes, computer, person):
    with client:
        response = client.patch('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                data=json.dumps(dict()),
                                content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_patch_relationship_not_list_missing_type(client, register_routes, computer, person):
    payload = {
        'data': {
            'id': str(person.person_id)
        }
    }

    with client:
        response = client.patch('/computers/' + str(computer.id) + '/relationships/owner',
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_patch_relationship_not_list_missing_id(client, register_routes, computer, person):
    payload = {
        'data': {
            'type': 'person'
        }
    }

    with client:
        response = client.patch('/computers/' + str(computer.id) + '/relationships/owner',
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_patch_relationship_not_list_wrong_type(client, register_routes, computer, person):
    payload = {
        'data': {
            'type': 'error',
            'id': str(person.person_id)
        }
    }

    with client:
        response = client.patch('/computers/' + str(computer.id) + '/relationships/owner',
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 409


def test_patch_relationship_missing_type(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'id': str(computer.id)
            }
        ]
    }

    with client:
        response = client.patch('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_patch_relationship_missing_id(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'type': 'computer',
            }
        ]
    }

    with client:
        response = client.patch('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_patch_relationship_wrong_type(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'type': 'error',
                'id': str(computer.id)
            }
        ]
    }

    with client:
        response = client.patch('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                data=json.dumps(payload),
                                content_type='application/vnd.api+json')
        assert response.status_code == 409


def test_delete_relationship_no_data(client, register_routes, computer, person):
    with client:
        response = client.delete('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                 data=json.dumps(dict()),
                                 content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_delete_relationship_not_list_missing_type(client, register_routes, computer, person):
    payload = {
        'data': {
            'id': str(person.person_id)
        }
    }

    with client:
        response = client.delete('/computers/' + str(computer.id) + '/relationships/owner',
                                 data=json.dumps(payload),
                                 content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_delete_relationship_not_list_missing_id(client, register_routes, computer, person):
    payload = {
        'data': {
            'type': 'person'
        }
    }

    with client:
        response = client.delete('/computers/' + str(computer.id) + '/relationships/owner',
                                 data=json.dumps(payload),
                                 content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_delete_relationship_not_list_wrong_type(client, register_routes, computer, person):
    payload = {
        'data': {
            'type': 'error',
            'id': str(person.person_id)
        }
    }

    with client:
        response = client.delete('/computers/' + str(computer.id) + '/relationships/owner',
                                 data=json.dumps(payload),
                                 content_type='application/vnd.api+json')
        assert response.status_code == 409


def test_delete_relationship_missing_type(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'id': str(computer.id)
            }
        ]
    }

    with client:
        response = client.delete('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                 data=json.dumps(payload),
                                 content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_delete_relationship_missing_id(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'type': 'computer',
            }
        ]
    }

    with client:
        response = client.delete('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                 data=json.dumps(payload),
                                 content_type='application/vnd.api+json')
        assert response.status_code == 400


def test_delete_relationship_wrong_type(client, register_routes, computer, person):
    payload = {
        'data': [
            {
                'type': 'error',
                'id': str(computer.id)
            }
        ]
    }

    with client:
        response = client.delete('/persons/' + str(person.person_id) + '/relationships/computers?include=computers',
                                 data=json.dumps(payload),
                                 content_type='application/vnd.api+json')
        assert response.status_code == 409


def test_base_data_layer():
    base_dl = BaseDataLayer()
    with pytest.raises(NotImplementedError):
        base_dl.create_object(None, None, **dict())
    with pytest.raises(NotImplementedError):
        base_dl.get_object(**dict())
    with pytest.raises(NotImplementedError):
        base_dl.get_collection(None, **dict())
    with pytest.raises(NotImplementedError):
        base_dl.update_object(None, None, None, **dict())
    with pytest.raises(NotImplementedError):
        base_dl.delete_object(None, **dict())
    with pytest.raises(NotImplementedError):
        base_dl.create_relationship(None, None, None, **dict())
    with pytest.raises(NotImplementedError):
        base_dl.get_relationship(None, None, None, **dict())
    with pytest.raises(NotImplementedError):
        base_dl.update_relationship(None, None, None, **dict())
    with pytest.raises(NotImplementedError):
        base_dl.delete_relationship(None, None, None, **dict())


def test_qs_manager():
    with pytest.raises(ValueError):
        QSManager([])
