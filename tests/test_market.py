"""Tests for source semantics and joins that could change a commercial conclusion."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build',ROOT/'scripts/build.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class MarketChecks(unittest.TestCase):
    def test_suppressed_is_not_zero_and_invalid_values_fail(self):
        self.assertEqual(module.number('-'),0)
        for raw in ['X','...','..',None]:self.assertIsNone(module.number(raw))
        for raw in ['-1','nan','inf','unknown']:
            with self.assertRaises(ValueError):module.number(raw)

    def test_zero_denominator_remains_undefined(self):
        self.assertIsNone(module.safe_ratio(5,0))
        self.assertIsNone(module.safe_ratio(None,10))
        self.assertEqual(module.safe_ratio(0,10),0)

    def test_snapshot_preserves_unique_local_units_not_enterprises(self):
        d=json.loads((ROOT/'data/processed/market.json').read_text())
        self.assertEqual(len(d['states']),81)
        n=next(r for r in d['national'] if r['year']==2024)
        self.assertEqual(n['rental_sites'],4264)
        self.assertEqual(n['rental_companies'],4131)
        self.assertEqual(sum(r['rental_sites'] for r in d['states'] if r['year']==2024),n['rental_sites'])
        self.assertEqual(sum(c['type']=='exact' for c in json.loads((ROOT/'data/qa.json').read_text())['reconciliations']),15)

    def test_sql_join_cannot_multiply_locations_by_number_of_crops(self):
        # Aggregate the four crop records before joining to one state-year location count.
        db=sqlite3.connect(ROOT/'data/processed/market.sqlite')
        totals=list(db.execute('''WITH crop AS (SELECT state_id,year,SUM(planted_ha) area FROM crops GROUP BY state_id,year)
          SELECT r.year,SUM(r.sites),SUM(c.area),COUNT(*) FROM rental r JOIN crop c USING(state_id,year) GROUP BY r.year'''))
        self.assertEqual(len(totals),3)
        expected={2022:3418,2023:3804,2024:4264}
        for year,sites,area,count in totals:
            self.assertEqual(sites,expected[year]);self.assertEqual(count,27)
        self.assertEqual(totals[-1][2],79683294)
        db.close()

    def test_share_uses_national_denominator_and_selected_crops(self):
        d=json.loads((ROOT/'data/processed/market.json').read_text())
        n=next(r for r in d['national'] if r['year']==2024)
        mt=next(r for r in d['states'] if r['year']==2024 and r['state_id']=='51')
        self.assertAlmostEqual(100*sum(mt['crop_area_ha'].values())/sum(n['crop_area_ha'].values()),26.56943345,places=6)
        self.assertAlmostEqual(100*mt['rental_sites']/n['rental_sites'],6.26172608,places=6)
        self.assertNotEqual(mt['rental_sites'],n['rental_companies'])


if __name__=='__main__':unittest.main()
