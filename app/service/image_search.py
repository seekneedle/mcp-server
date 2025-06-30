from service.retrieve_needle import retrieve_needle

def image_search(query):
    results = retrieve_needle(query, index_id='')
