import strawberry
from django.db.models import Case, When, Q, Value
from strawberry import Info

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from .models import Project


@strawberry_django.interface(Project)
class ProjectType:
    topic: strawberry.auto

    @classmethod
    def get_queryset(cls, qs, info: Info):
        return qs.annotate(
            _Project__typename=Case(
                When(~Q(artist=''), then=Value('ArtProjectType')),
                When(~Q(supervisor=''), then=Value('ResearchProjectType')),
            )
        )


@strawberry_django.type(Project)
class ArtProjectType(ProjectType):
    artist: strawberry.auto


@strawberry_django.type(Project)
class ResearchProjectType(ProjectType):
    supervisor: strawberry.auto


@strawberry.type
class Query:
    projects: list[ProjectType] = strawberry_django.field()


schema = strawberry.Schema(
    query=Query,
    types=[ArtProjectType, ResearchProjectType],
    extensions=[DjangoOptimizerExtension],
)
