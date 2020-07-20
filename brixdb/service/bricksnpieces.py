import requests


def bricksnpieces_cookies(country='no'):
    """
    Bricks&Pieces requires a couple of cookies to be set to fetch data.
    State 3 is sale.
    """
    return {'csAgeAndCountry': '{"age":"18","countrycode":"%s"}' % country.upper(),
            'csRpFlowState': '{"state":3}', 'country': country.upper(), 'AGE_GATE': 'grown_up'}


def get_element_prices(element, desired_quantity=1, country='no'):
    """
    Fetches price information for the given Element from Bricks&Pieces, which
    has its own set of stupidity.
    """
    # obviously this requires at least one element id to work
    if not element.lego_ids:
        return {}
    # TODO: find a good way of storing the currently active element id in case
    #       it's not the highest number
    element_id = sorted(element.lego_ids, reverse=True)[0]
    cookies = bricksnpieces_cookies(country=country)
    # url = 'https://www.lego.com/nb-no/service/rpservice/getitemordesign?issalesflow=true&itemordesignnumber={item}'
    args = [element_id, country.upper()]
    url = 'https://bricksandpieces.services.lego.com/api/v1/bricks/items/{}?country={}&orderType=buy'.format(*args)
    response = requests.get(url.format(item=element_id), cookies=cookies)
    if response.status_code != 200:
        return []
    item = response.json()['Bricks'][0]
    return {'price': item['Price'], 'quantity': item['SQty']}


def get_part_prices(design_id):
    """
    Get all prices for a design id.
    """
    item = response.json()['Bricks']
    return data 
