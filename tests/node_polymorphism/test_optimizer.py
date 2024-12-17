import pytest

from .models import ArtProject, ResearchProject
from .schema import schema
from ..utils import assert_num_queries


@pytest.mark.django_db(transaction=True)
def test_polymorphic_interface_query():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            topic
            ... on ArtProjectType {
              artist
            }
            ... on ResearchProjectType {
              supervisor
            }
          }
        }
      }
    }
    """

    with assert_num_queries(4):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "topic": ap.topic,
                        "artist": ap.artist,
                    }
                },
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "topic": rp.topic,
                        "supervisor": rp.supervisor,
                    }
                },
            ]
        }
    }
