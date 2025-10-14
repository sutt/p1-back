Getting the following error when posting new data from the client, how to fix?

sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) <class 'asyncpg.exceptions.UniqueViolationError'>: duplicate key value violates unique constraint "shapes_pkey"
DETAIL:  Key (id)=(rect1) already exists.
[SQL: INSERT INTO shapes (id, type, x, y, width, height, radius, "selectedBy") VALUES ($1::VARCHAR, $2::VARCHAR, $3::INTEGER, $4::INTEGER, $5::INTEGER, $6::INTEGER, $7::INTEGER, $8::VARCHAR[])]
[parameters: [('rect1', 'rectangle', 100, 100, 300, 200, None, []), ('circ1', 'circle', 600, 400, None, None, 100, ['User2']), ('shape_1760392312198', 'circle', 654, 101, None, None, 287, [])]]
(Background on this error at: https://sqlalche.me/e/20/gkpj)

add a demo_update.py script which hits the api with some data duplicated from seed.py to test that your proposed fix work