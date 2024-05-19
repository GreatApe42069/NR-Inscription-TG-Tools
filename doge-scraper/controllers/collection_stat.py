import concurrent.futures
from collections import defaultdict
from typing import Union, List
import requests

from utils.constants import BASE_URL

class CollectionController:
    @staticmethod
    def get_inscription_data(inscription_id: str) -> Union[dict, None]:
        """Fetches the inscription data from the API"""
        # API URL for fetching the outpointing and address
        outpoint_url = f"{BASE_URL}/inscription/{inscription_id}/outpoint"
        # API URL for fetching the name
        name_url = f"{BASE_URL}/inscription/{inscription_id}"

        # Fetching the data
        outpoint_response = requests.get(outpoint_url)
        name_response = requests.get(name_url, timeout=120)

        if not outpoint_response.ok or not name_response.ok:
            return None

        outpoint_data = outpoint_response.json()
        name_data = name_response.json()

        # Extract the address and name
        address = outpoint_data.get('inscription', {}).get('address', 'Not Found')
        name = name_data.get('meta', {}).get('name', 'Not Found')

        return {
            'id': inscription_id,
            'address': address,
            'name': name
        }

    @staticmethod
    def get_collection_inscriptions(collection_slug: str, skip: int, limit: int) -> List[str]:
        """Gets the list of inscription IDs for the given collection"""
        api_url = f"{BASE_URL}/collection/{collection_slug}/inscriptions"
        response = requests.get(api_url)

        if not response.ok:
            return []

        inscription_ids = [inscription['id'] for inscription in response.json()]
        print(len(inscription_ids))
        inscription_ids.sort()
        print(f"inscription_ids len is {len(inscription_ids)}")
        return inscription_ids[skip:limit]

    def get_collection_data(self, collection_slug: str, skip: int, limit: int) -> List[dict]:
        """Gets the data for the collection"""
        inscription_ids = self.get_collection_inscriptions(
            collection_slug=collection_slug,
            skip=skip,
            limit=limit
        )

        print(f"Found {len(inscription_ids)} IDs fetching the data")
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            collection_data = list(executor.map(self.get_inscription_data, inscription_ids))

        collection_dict = defaultdict(list)
        for data in collection_data:
            dict_key = f'{data["address"]}_{data["id"]}'
            collection_dict[dict_key].append(data)

        response = [{
            "address": key.split("_")[0],
            "id": key.split("_")[1],
            "names": [v["name"] for v in value],
            "amount": len(value)
        } for key, value in collection_dict.items()]

        return response
