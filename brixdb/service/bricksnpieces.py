import requests


def get_element_prices(element, desired_quantity=1):
    """
    Fetches price information for the given Element from Bricks&Pieces, which
    has its own set of stupidity.
    """
    # obviously this requires at least one element id to work
    if not element.lego_ids:
        return {}
    element_id = sorted(element.lego_ids, reverse=True)[0]
    cookies = {'csAgeAndCountry': '{"age":"36","countrycode":"NO"}',  'csRpFlowState': '{"state":3}'}
    url = 'https://www.lego.com/nb-NO/service/rpservice/getitemordesign?isSalesFlow=true&itemordesignnumber={item}'
    response = requests.get(url.format(item=element_id), cookies=cookies)
    item = response.json()['Bricks'][0]
    return {'price': item['Price'], 'quantity': item['SQty']}

