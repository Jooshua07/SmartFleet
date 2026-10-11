from database.connection import get_connection

with get_connection() as conn:
    with conn.cursor() as cursor:

        # Inspect both tables
        for table in ["buses", "routes"]:
            print(f"\n--- {table.upper()} COLUMNS ---")

            cursor.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    is_identity
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                ORDER BY ordinal_position;
            """, (table,))

            for row in cursor.fetchall():
                print(row)

        # Inspect constraints
        print("\n--- BUSES CONSTRAINTS ---")

        cursor.execute("""
            SELECT
                conname,
                pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'public.buses'::regclass;
        """)

        for row in cursor.fetchall():
            print(row)

        # Inspect valid bus status values
        print("\n--- STATUS RULES ---")

        cursor.execute("""
            SELECT
                conname,
                pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'public.buses'::regclass
              AND contype = 'c';
        """)

        for row in cursor.fetchall():
            print(row)

        # Inspect existing routes
        print("\n--- EXISTING ROUTES ---")

        cursor.execute("SELECT * FROM public.routes LIMIT 10;")

        for row in cursor.fetchall():
            print(row)