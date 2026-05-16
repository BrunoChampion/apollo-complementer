import respx
from httpx import Response

from app.core.config import Settings
from app.integrations.apollo.factory import build_apollo_client
from app.integrations.apollo.fake import FakeApolloClient
from app.integrations.apollo.http import HttpApolloClient


class TestFakeApolloClient:
    def test_search_people_returns_fake_results(self) -> None:
        client = FakeApolloClient()
        result = client.search_people(
            person_titles=["CEO", "CTO"],
            person_locations=["Argentina"],
            page=1,
            per_page=10,
        )
        assert "people" in result
        assert len(result["people"]) == 3
        assert result["people"][0]["title"] == "CEO"
        assert "pagination" in result
        assert result["pagination"]["total_entries"] == 3

    def test_search_companies_returns_fake_results(self) -> None:
        client = FakeApolloClient()
        result = client.search_companies(
            q_organization_name="Acme",
            organization_locations=["Argentina"],
            page=1,
            per_page=10,
        )
        assert "organizations" in result
        assert len(result["organizations"]) == 2
        assert result["organizations"][0]["name"] == "Acme"

    def test_enrich_organization_returns_fake_data(self) -> None:
        client = FakeApolloClient()
        result = client.enrich_organization(domain="acme.com")
        assert "organization" in result
        assert result["organization"]["website_url"] == "acme.com"

    def test_enrich_person_returns_fake_data(self) -> None:
        client = FakeApolloClient()
        result = client.enrich_person(email="juan@example.com")
        assert "person" in result
        assert result["person"]["email"] == "juan@example.com"


class TestHttpApolloClient:
    @respx.mock
    def test_search_people(self) -> None:
        route = respx.post("https://api.apollo.io/api/v1/mixed_people/api_search").mock(
            return_value=Response(
                200,
                json={
                    "people": [{"id": "p1", "name": "Ana"}],
                    "pagination": {"page": 1, "per_page": 25, "total_entries": 1, "total_pages": 1},
                },
            )
        )
        client = HttpApolloClient(api_key="test-key")
        result = client.search_people(person_titles=["CEO"])
        assert result["people"][0]["name"] == "Ana"
        assert route.called

    @respx.mock
    def test_search_companies(self) -> None:
        route = respx.post("https://api.apollo.io/api/v1/mixed_companies/search").mock(
            return_value=Response(
                200,
                json={
                    "organizations": [{"id": "o1", "name": "Acme"}],
                    "pagination": {"page": 1, "per_page": 25, "total_entries": 1, "total_pages": 1},
                },
            )
        )
        client = HttpApolloClient(api_key="test-key")
        result = client.search_companies(q_organization_name="Acme")
        assert result["organizations"][0]["name"] == "Acme"
        assert route.called

    @respx.mock
    def test_enrich_organization(self) -> None:
        route = respx.get("https://api.apollo.io/api/v1/organizations/enrich").mock(
            return_value=Response(
                200,
                json={"organization": {"id": "o1", "name": "Acme"}},
            )
        )
        client = HttpApolloClient(api_key="test-key")
        result = client.enrich_organization(domain="acme.com")
        assert result["organization"]["name"] == "Acme"
        assert route.called

    @respx.mock
    def test_enrich_person(self) -> None:
        route = respx.post("https://api.apollo.io/api/v1/people/match").mock(
            return_value=Response(
                200,
                json={"person": {"id": "p1", "name": "Ana"}},
            )
        )
        client = HttpApolloClient(api_key="test-key")
        result = client.enrich_person(email="ana@example.com")
        assert result["person"]["name"] == "Ana"
        assert route.called

    @respx.mock
    def test_rate_limit_retry(self) -> None:
        route = respx.post("https://api.apollo.io/api/v1/mixed_people/api_search").mock(
            side_effect=[
                Response(429, json={"error": "rate limit"}),
                Response(
                    200,
                    json={
                        "people": [{"id": "p1"}],
                        "pagination": {
                            "page": 1,
                            "per_page": 25,
                            "total_entries": 1,
                            "total_pages": 1,
                        },
                    },
                ),
            ]
        )
        client = HttpApolloClient(api_key="test-key")
        result = client.search_people()
        assert result["people"][0]["id"] == "p1"
        assert route.call_count == 2


class TestApolloFactory:
    def test_build_without_key_returns_fake(self) -> None:
        settings = Settings(apollo_api_key="")
        client = build_apollo_client(settings)
        assert isinstance(client, FakeApolloClient)

    def test_build_with_placeholder_key_returns_fake(self) -> None:
        settings = Settings(apollo_api_key="replace-with-apollo-api-key-or-leave-empty")
        client = build_apollo_client(settings)
        assert isinstance(client, FakeApolloClient)

    def test_build_with_key_returns_http(self) -> None:
        settings = Settings(apollo_api_key="sk-test")
        client = build_apollo_client(settings)
        assert isinstance(client, HttpApolloClient)
