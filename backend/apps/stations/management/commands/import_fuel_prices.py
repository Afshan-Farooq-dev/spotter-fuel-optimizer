import csv
import json
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from ...services.importing import import_fuel_csv


class Command(BaseCommand):
    help = "Import a fuel-price CSV using the documented median-price policy."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            result = import_fuel_csv(options["path"], dry_run=options["dry_run"])
        except (OSError, ValueError, csv.Error, ValidationError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, indent=2))
