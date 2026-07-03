import unittest
from pathlib import Path

from saudi_data_extract import (
    SAUDI_BBOX,
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


if __name__ == "__main__":
    unittest.main()
