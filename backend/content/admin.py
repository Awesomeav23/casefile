"""Read-only admin for imported content. Content changes only through `import_case`."""

from django.contrib import admin

from . import models as m


class ReadOnlyMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReadOnlyAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_filter = ["case"]
    search_fields = ["key"]


class ReadOnlyInline(ReadOnlyMixin, admin.TabularInline):
    extra = 0


class OptionInline(ReadOnlyInline):
    model = m.AccusationOption


class AnswerKeyInline(ReadOnlyMixin, admin.StackedInline):
    model = m.AnswerKey
    verbose_name = "answer key (spoiler)"


class HintInline(ReadOnlyInline):
    model = m.Hint


@admin.register(m.Case)
class CaseAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ["slug", "title", "status", "difficulty", "content_version", "published_at"]
    list_filter = ["status", "difficulty"]
    search_fields = ["slug", "title"]


@admin.register(m.CaseImport)
class CaseImportAdmin(ReadOnlyAdmin):
    list_display = ["case", "content_version", "breaking", "imported_by", "imported_at"]
    search_fields = ["case__slug"]


@admin.register(m.Person)
class PersonAdmin(ReadOnlyAdmin):
    list_display = ["key", "name", "role", "is_suspect", "case"]


@admin.register(m.Location)
class LocationAdmin(ReadOnlyAdmin):
    list_display = ["key", "name", "case"]


@admin.register(m.Evidence)
class EvidenceAdmin(ReadOnlyAdmin):
    list_display = ["key", "title", "kind", "location", "case"]
    list_filter = ["case", "kind"]


@admin.register(m.Topic)
class TopicAdmin(ReadOnlyAdmin):
    list_display = ["key", "person", "prompt", "case"]


@admin.register(m.Statement)
class StatementAdmin(ReadOnlyAdmin):
    list_display = ["key", "person", "topic", "reaction_evidence", "case"]


@admin.register(m.TimelineEvent)
class TimelineEventAdmin(ReadOnlyAdmin):
    list_display = ["key", "title", "starts_at", "ends_at", "certainty", "case"]


@admin.register(m.AccusationQuestion)
class AccusationQuestionAdmin(ReadOnlyAdmin):
    list_display = ["key", "kind", "required_for_solve", "case"]
    inlines = [OptionInline, AnswerKeyInline]


@admin.register(m.Contradiction)
class ContradictionAdmin(ReadOnlyAdmin):
    list_display = ["key", "statement", "conflicts_evidence", "conflicts_statement", "case"]


@admin.register(m.CaseSolution)
class CaseSolutionAdmin(ReadOnlyAdmin):
    list_display = ["case"]
    search_fields = ["case__slug"]


@admin.register(m.RedHerring)
class RedHerringAdmin(ReadOnlyAdmin):
    list_display = ["person", "case"]
    search_fields = ["person__key"]


@admin.register(m.HintTrack)
class HintTrackAdmin(ReadOnlyAdmin):
    list_display = ["key", "goal", "priority", "case"]
    inlines = [HintInline]
