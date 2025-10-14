Add an create/update route for "/shapes" which will pass the full shapes array and the username from the client from a client and write it to the DB.

request:
{
    user: str,  # e.g. "User3"
    data: Shapes[] # e.g. [Shape(id='rect1', type='rectangle', x=100, y=100, width=300, height=200, selectedBy=[]),Shape(id='circ1', type='circle', x=600, y=400, radius=100, selectedBy=['User2']),]
}