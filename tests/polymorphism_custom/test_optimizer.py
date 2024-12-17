import pytest

from .models import Project
from .schema import schema
from ..utils import assert_num_queries


@pytest.mark.django_db(transaction=True)
def test_polymorphic_interface_query():
    ap = Project.objects.create(topic="Art", artist="Artist")
    rp = Project.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
        __typename
        topic
        ... on ArtProjectType {
          artist
        }
        # ... on ResearchProjectType {
        #   supervisor
        # }
      }
    }
    """

    with assert_num_queries(1):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": [
            {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist},
            {
                "__typename": "ResearchProjectType",
                "topic": rp.topic,
                "supervisor": rp.supervisor,
            },
        ]
    }


