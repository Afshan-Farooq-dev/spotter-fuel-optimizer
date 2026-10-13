import csv
from decimal import Decimal
from unittest.mock import patch
import pytest
from apps.stations.models import FuelDataset, FuelPrice, FuelStation
from apps.stations.services.fuel_data import COLUMNS
from apps.stations.services.importing import import_fuel_csv


def source(tmp_path):
    p = tmp_path / "fuel.csv"
    with p.open("w", newline="") as stream:
        writer = csv.writer(stream); writer.writerow(COLUMNS)
        writer.writerows([["1","Stop","Road","Town","TX","1","2.01"],
                          ["1","Stop","Road","Town","TX","2","4.01"],
                          ["2","Canadian","Road","Town","ON","1","5"]])
    return p


@pytest.mark.django_db
def test_import_repeat_and_dry_run(tmp_path):
    p = source(tmp_path)
    assert import_fuel_csv(p, dry_run=True)["status"] == "dry_run"
    assert FuelDataset.objects.count() == 0
    assert import_fuel_csv(p)["status"] == "imported"
    assert import_fuel_csv(p)["status"] == "already_imported"
    assert (FuelDataset.objects.count(), FuelStation.objects.count(), FuelPrice.objects.count()) == (1,1,2)
    assert FuelStation.objects.get().median_price == Decimal("3.01")


@pytest.mark.django_db
def test_failed_import_rolls_back(tmp_path):
    with patch.object(FuelPrice.objects, "bulk_create", side_effect=RuntimeError("test failure")):
        with pytest.raises(RuntimeError):
            import_fuel_csv(source(tmp_path))
    assert FuelDataset.objects.count() == FuelStation.objects.count() == FuelPrice.objects.count() == 0


@pytest.mark.django_db
def test_new_snapshot_keeps_historical_prices(tmp_path):
    p = source(tmp_path)
    import_fuel_csv(p)
    p.write_text(p.read_text().replace("4.01","6.01"))
    import_fuel_csv(p)
    assert FuelStation.objects.count() == 1
    assert FuelPrice.objects.count() == 4
    assert FuelStation.objects.get().median_price == Decimal("4.01")
