# Generated manually - Fix Contract model primary key
#
# The issue: contract_id was the primary key, but the same contract_id can appear
# for multiple characters (e.g., issuer and acceptor), causing unique constraint violations.
#
# The fix:
# 1. Add a new surrogate 'id' field as primary key
# 2. Convert contract_id from primary key to a regular indexed field
# 3. Add unique_together on (character_id, contract_id)
#
# Note: ContractItem has a foreign key to Contract that we need to update.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_remove_mptt_from_character_asset'),
    ]

    operations = [
        # Step 1: Add a new id column, drop PK, add constraints
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        -- Create a sequence for the new id column
                        CREATE SEQUENCE IF NOT EXISTS core_contract_id_seq;

                        -- Add the new id column as a nullable bigint
                        ALTER TABLE core_contract ADD COLUMN id BIGINT;

                        -- Fill the id column with sequential values based on contract_id ordering
                        WITH numbered_rows AS (
                            SELECT contract_id, ROW_NUMBER() OVER (ORDER BY contract_id) as row_num
                            FROM core_contract
                        )
                        UPDATE core_contract c
                        SET id = nr.row_num
                        FROM numbered_rows nr
                        WHERE c.contract_id = nr.contract_id;

                        -- Make the column NOT NULL
                        ALTER TABLE core_contract ALTER COLUMN id SET NOT NULL;

                        -- Set the default to use the sequence
                        ALTER TABLE core_contract ALTER COLUMN id SET DEFAULT nextval('core_contract_id_seq');

                        -- Set the sequence to start from the max id + 1
                        SELECT setval('core_contract_id_seq', COALESCE((SELECT MAX(id) FROM core_contract), 0) + 1, false);
                    """,
                    reverse_sql="""
                        ALTER TABLE core_contract ALTER COLUMN id DROP DEFAULT;
                        DROP SEQUENCE IF EXISTS core_contract_id_seq;
                        ALTER TABLE core_contract DROP COLUMN id;
                    """
                ),
                # Step 2: Drop the foreign key constraint from ContractItem
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE core_contractitem
                        DROP CONSTRAINT IF EXISTS core_contractitem_contract_id_ba661882_fk_core_cont;
                    """,
                    reverse_sql="""
                        -- No-op for reverse
                    """
                ),
                # Step 3: Update ContractItem to reference the new id column instead of contract_id
                migrations.RunSQL(
                    sql="""
                        -- The contract_id column in ContractItem currently stores the old PK value (Contract.contract_id)
                        -- We need to update it to store the new PK value (Contract.id)
                        UPDATE core_contractitem ci
                        SET contract_id = c.id
                        FROM core_contract c
                        WHERE ci.contract_id = c.contract_id;
                    """,
                    reverse_sql="""
                        -- Reverse: update back to reference contract_id
                        UPDATE core_contractitem ci
                        SET contract_id = c.contract_id
                        FROM core_contract c
                        WHERE ci.contract_id = c.id;
                    """
                ),
                # Step 4: Drop the old primary key and add the new one
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE core_contract DROP CONSTRAINT core_contract_pkey;
                        ALTER TABLE core_contract ADD CONSTRAINT core_contract_pkey PRIMARY KEY (id);
                    """,
                    reverse_sql="""
                        ALTER TABLE core_contract DROP CONSTRAINT core_contract_pkey;
                        ALTER TABLE core_contract ADD CONSTRAINT core_contract_pkey PRIMARY KEY (contract_id);
                    """
                ),
                # Step 5: Re-add the foreign key constraint (now references the new id column)
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE core_contractitem
                        ADD CONSTRAINT core_contractitem_contract_id_fk_core_contract
                        FOREIGN KEY (contract_id) REFERENCES core_contract(id) ON DELETE CASCADE;
                    """,
                    reverse_sql="""
                        ALTER TABLE core_contractitem
                        DROP CONSTRAINT IF EXISTS core_contractitem_contract_id_fk_core_contract;
                    """
                ),
                # Step 6: Add index on contract_id (for lookups)
                migrations.RunSQL(
                    sql="""
                        CREATE INDEX IF NOT EXISTS core_contract_contract_id_idx ON core_contract(contract_id);
                    """,
                    reverse_sql="""
                        DROP INDEX IF EXISTS core_contract_contract_id_idx;
                    """
                ),
                # Step 7: Add unique constraint on (character_id, contract_id)
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE core_contract ADD CONSTRAINT core_contract_character_contract_id_uniq
                        UNIQUE (character_id, contract_id);
                    """,
                    reverse_sql="""
                        ALTER TABLE core_contract DROP CONSTRAINT IF EXISTS core_contract_character_contract_id_uniq;
                    """
                ),
            ],
            state_operations=[
                # Tell Django about the new model structure
                migrations.AddField(
                    model_name='contract',
                    name='id',
                    field=models.BigAutoField(primary_key=True, serialize=False),
                ),
                migrations.AlterField(
                    model_name='contract',
                    name='contract_id',
                    field=models.BigIntegerField(db_index=True),
                ),
            ],
        ),
    ]
