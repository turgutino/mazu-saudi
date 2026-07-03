import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from saudi_data_extract import (
    SAUDI_BBOX,
    discover_files,
    infer_dataset_id,
    is_metadata_path,
    safe_output_name,
)


class PathUtilityTests(unittest.TestCase):
    def test_saudi_bbox_matches_project_region(self):
        self.assertEqual(SAUDI_BBOX["lat_min"], 16.0)
        self.assertEqual(SAUDI_BBOX["lat_max"], 32.0)
        self.assertEqual(SAUDI_BBOX["lon_min"], 34.0)
        self.assertEqual(SAUDI_BBOX["lon_max"], 56.0)

    def test_is_metadata_path_skips_appledouble(self):
        self.assertTrue(is_metadata_path(Path("._file.nc")))
        self.assertTrue(is_metadata_path(Path("/data/._202501")))
        self.assertFalse(is_metadata_path(Path("/data/202501/file.nc")))

    def test_safe_output_name_keeps_dataset_and_stem(self):
        path = Path(
            "/root/10_SATE_PRECIPITATION_PRODUCT_2025/202509/"
            "FYMERG_S_202509010000_E202509010029.h5"
        )
        self.assertEqual(
            safe_output_name("ds10", path),
            "saudi_ds10_FYMERG_S_202509010000_E202509010029.nc",
        )

    def test_infer_dataset_id_from_top_level_dir(self):
        self.assertEqual(
            infer_dataset_id(Path("/x/1_NAFP_ART_ATM_GLB_MONTH_PROD/202506/a.grib2")),
            "ds1",
        )
        self.assertEqual(
            infer_dataset_id(
                Path("/x/11_TCGD_MON_GLB_PROD/20251001/t00z.20251001/track_1_0.txt")
            ),
            "ds11",
        )


class DiscoveryTests(unittest.TestCase):
    def test_discover_files_finds_supported_layouts_and_skips_metadata(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._touch(root / "1_NAFP_ART_ATM_GLB_MONTH_PROD/202501/a.grib2")
            self._touch(root / "1_NAFP_ART_ATM_GLB_MONTH_PROD/202501/._a.grib2")
            self._touch(root / "2_NAFP_ART_SFC_GLB_DAY_PROD/20250101/b.grib2")
            self._touch(root / "3_NAFP_ART_SFC_GLB_MONTH_PROD/202501/c.grib2")
            self._touch(root / "4_OCEA_FUS_DAY_PRO/20250101/d.nc")
            self._touch(root / "10_SATE_PRECIPITATION_PRODUCT_2025/202501/e.h5")
            self._touch(
                root
                / "11_TCGD_MON_GLB_PROD/20251001/t00z.20251001/track_1_0.txt"
            )
            self._touch(
                root
                / "11_TCGD_MON_GLB_PROD/20251001/t00z.20251001/._track_2_0.txt"
            )

            records = discover_files(root)

        datasets = [record["dataset"] for record in records]
        paths = [record["path"].name for record in records]
        self.assertEqual(datasets, ["ds1", "ds2", "ds3", "ds4", "ds10", "ds11"])
        self.assertNotIn("._a.grib2", paths)
        self.assertNotIn("._track_2_0.txt", paths)

    def test_discover_files_filters_datasets_and_periods(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._touch(root / "10_SATE_PRECIPITATION_PRODUCT_2025/202501/jan.h5")
            self._touch(root / "10_SATE_PRECIPITATION_PRODUCT_2025/202502/feb.h5")
            self._touch(root / "2_NAFP_ART_SFC_GLB_DAY_PROD/20250101/day.grib2")

            records = discover_files(root, datasets={"ds10"}, start="202502", end="202502")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["dataset"], "ds10")
        self.assertEqual(records[0]["period"], "202502")
        self.assertEqual(records[0]["path"].name, "feb.h5")

    def _touch(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sample", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
