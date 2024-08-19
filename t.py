import yaml
import os
import requests


# Grafana class to manage teams and users in Grafana
class Grafana:
    def __init__(self, grafana_url, sa_token):
        self.grafana_url = grafana_url
        self.headers = {
            'Authorization': f'Bearer {sa_token}',
            'Content-Type': 'application/json'
        }

    def get_teams(self):
        """Fetches a list of all teams from Grafana."""
        url = f'{self.grafana_url}/api/teams/search'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        teams = response.json()['teams']
        return teams

    def create_team_if_not_exists(self, team_name):
        """Creates a team if it doesn't exist."""
        teams = self.get_teams()
        for team in teams:
            if team['name'].lower() == team_name.lower():
                return team['id']  # Return the existing team's ID
        # Team does not exist, create it
        url = f'{self.grafana_url}/api/teams'
        payload = {'name': team_name}
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()['teamId']

    def add_user_to_team_if_not_exists(self, team_id, user_login):
        """Adds a user to a team if the user is not already a member."""
        url = f'{self.grafana_url}/api/teams/{team_id}/members'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        users = response.json()
        for user in users:
            if user['login'].lower() == user_login.lower():
                return  # User already in the team, do nothing
        # User is not in the team, add them
        payload = {'userLogin': user_login}
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()


# MS Graph class to interact with Microsoft Graph API
class MSGraph:
    def __init__(self, subscription_key):
        self.subscription_key = subscription_key
        self.headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json'
        }
        self.base_url = 'https://graph.microsoft.com/v1.0'

    def get_group_users(self, group_name):
        """Fetches users for a specific group by its display name."""
        url = f'{self.base_url}/groups?$filter=displayName eq \'{group_name}\'&$expand=members'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        groups = response.json()['value']
        if groups:
            group = groups[0]
            return [member['mail'] for member in group['members'] if 'mail' in member and member['mail']]
        return []


# Function to read teams and AD groups from YAML file
def read_teams_and_ad_groups(file_path):
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)

    teams_and_groups = {}
    for team, properties in data.items():
        ad_groups = [value for key, value in properties.items() if key.startswith('ad-group')]
        teams_and_groups[team] = ad_groups

    return teams_and_groups


# Main function to orchestrate the creation and population of Grafana teams
def main():
    # Replace with your actual credentials and file path
    grafana_url = 'https://your-grafana-instance.com'
    sa_token = 'YOUR_GRAFANA_SA_TOKEN'
    subscription_key = 'YOUR_OCP_APIM_SUBSCRIPTION_KEY'
    teams_filename = 'teams.yaml'
    yaml_file_path = os.path.join(os.path.dirname(__file__), teams_filename)

    # Create instances of Grafana and MSGraph
    grafana = Grafana(grafana_url, sa_token)
    msgraph = MSGraph(subscription_key)

    # Read teams and AD groups from the YAML file
    teams_and_ad_groups = read_teams_and_ad_groups(yaml_file_path)

    # Iterate over each team and its associated AD groups
    for team_name, ad_groups in teams_and_ad_groups.items():
        print(f'Processing team: {team_name}')

        # Create the team in Grafana if it doesn't exist
        team_id = grafana.create_team_if_not_exists(team_name)

        # For each AD group, get users and add them to the Grafana team
        for ad_group in ad_groups:
            print(f'  Fetching users from AD group: {ad_group}')
            users = msgraph.get_group_users(ad_group)

            for user in users:
                print(f'    Adding user: {user} to team: {team_name}')
                grafana.add_user_to_team_if_not_exists(team_id, user)

    print('Done!')


if __name__ == "__main__":
    main()
