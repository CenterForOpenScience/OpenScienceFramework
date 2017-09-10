# -*- coding: utf-8 -*-
import mock
import pytest
from urlparse import urlparse

from django.http import HttpResponse
from rest_framework.test import APIRequestFactory

from api.base import settings
from api.base.middleware import CorsMiddleware
from osf_tests.factories import (
    PreprintProviderFactory,
    InstitutionFactory,
)
from tests.base import fake
from website.util import api_v2_url


class MiddlewareTestCase:
    MIDDLEWARE = None

    @pytest.fixture()
    def middleware(self):
        return self.MIDDLEWARE()

    @pytest.fixture()
    def request_factory(self):
        return APIRequestFactory()

@pytest.mark.django_db
class TestCorsMiddleware(MiddlewareTestCase):
    MIDDLEWARE = CorsMiddleware
    settings.CORS_ORIGIN_ALLOW_ALL = False

    @pytest.fixture()
    def url(self):
        return api_v2_url('users/me/')

    @pytest.fixture()
    def domain(self):
        return urlparse('https://dinosaurs.sexy')

    def test_institutions_added_to_cors_whitelist(self, request_factory, middleware, url, domain):
        institution = InstitutionFactory(
            domains=[domain.netloc.lower()],
            name="Institute for Sexy Lizards"
        )
        settings.load_origins_whitelist()
        request = request_factory.get(url, HTTP_ORIGIN=domain.geturl())
        response = HttpResponse()
        middleware.process_request(request)
        processed = middleware.process_response(request, response)
        assert response['Access-Control-Allow-Origin'] == domain.geturl()

    def test_preprintproviders_added_to_cors_whitelist(self, request_factory, middleware, url, domain):
        preprintprovider = PreprintProviderFactory(
            domain=domain.geturl().lower(),
            _id="DinoXiv"
        )
        settings.load_origins_whitelist()
        request = request_factory.get(url, HTTP_ORIGIN=domain.geturl())
        response = HttpResponse()
        middleware.process_request(request)
        processed = middleware.process_response(request, response)
        assert response['Access-Control-Allow-Origin'] == domain.geturl()

    def test_cross_origin_request_with_cookies_does_not_get_cors_headers(self, request_factory, middleware, url, domain):
        request = request_factory.get(url, HTTP_ORIGIN=domain.geturl())
        response = {}
        with mock.patch.object(request, 'COOKIES', True):
            middleware.process_request(request)
            processed = middleware.process_response(request, response)
        assert 'Access-Control-Allow-Origin' not in response

    def test_cross_origin_request_with_Authorization_gets_cors_headers(self, request_factory, middleware, url, domain):
        request = request_factory.get(
            url,
            HTTP_ORIGIN=domain.geturl(),
            HTTP_AUTHORIZATION="Bearer aqweqweohuweglbiuwefq"
        )
        response = HttpResponse()
        middleware.process_request(request)
        processed = middleware.process_response(request, response)
        assert response['Access-Control-Allow-Origin'] == domain.geturl()

    def test_cross_origin_request_with_Authorization_and_cookie_does_not_get_cors_headers(self, request_factory, middleware, url, domain):
        request = request_factory.get(
            url,
            HTTP_ORIGIN=domain.geturl(),
            HTTP_AUTHORIZATION="Bearer aqweqweohuweglbiuwefq"
        )
        response = {}
        with mock.patch.object(request, 'COOKIES', True):
            middleware.process_request(request)
            processed = middleware.process_response(request, response)
        assert 'Access-Control-Allow-Origin' not in response

    def test_non_institution_preflight_request_requesting_authorization_header_gets_cors_headers(self, request_factory, middleware, url, domain):
        request = request_factory.options(
            url,
            HTTP_ORIGIN=domain.geturl(),
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization'
        )
        response = HttpResponse()
        middleware.process_request(request)
        processed = middleware.process_response(request, response)
        assert response['Access-Control-Allow-Origin'] == domain.geturl()
