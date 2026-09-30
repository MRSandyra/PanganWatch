#!/usr/bin/env python3
"""Verify F2: Reference and master data."""

from panganwatch.db import get_postgres_connection


def main():
    conn = get_postgres_connection()
    cur = conn.cursor()

    # Seed counts
    cur.execute("select count(*) from ref.ref_provinsi")
    print("ref_provinsi:", cur.fetchone()[0])
    cur.execute("select count(*) from ref.ref_kabkota")
    print("ref_kabkota:", cur.fetchone()[0])
    cur.execute("select count(*) from ref.ref_crosswalk_wilayah")
    print("ref_crosswalk_wilayah:", cur.fetchone()[0])
    cur.execute("select count(*) from ref.ref_komoditas")
    print("ref_komoditas:", cur.fetchone()[0])
    cur.execute("select count(*) from ref.ref_komoditas_alias")
    print("ref_komoditas_alias:", cur.fetchone()[0])

    # Bbox check
    cur.execute(
        "select count(*) from ref.ref_provinsi where lat < -11 or lat > 6 or lon < 95 or lon > 141"
    )
    print("outside_bbox:", cur.fetchone()[0])

    # Match method stats
    cur.execute(
        "select match_method, count(*) from ref.ref_crosswalk_wilayah group by match_method order by match_method"
    )
    for row in cur.fetchall():
        print("match:", row)

    conn.close()


if __name__ == "__main__":
    main()
