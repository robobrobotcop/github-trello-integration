import json
import requests
import pr_config

def main():

    github_url = 'https://api.github.com/orgs/billogram/issues?filter=all'
    github_header = pr_config.github_header

    trello_url = 'https://api.trello.com/1'
    trello_key = pr_config.trello_key
    trello_token = pr_config.trello_token
    trello_open = pr_config.trello_open
    trello_onhold = pr_config.trello_onhold
    trello_approved = pr_config.trello_approved

    ids_open = {}
    ids_onhold = {}
    ids_approved = {}

    # get all existing trello cards and their GitHub id
    response = requests.get('{}/lists/{}/cards'.format(trello_url, trello_open), params={'fields': 'all', 'key': trello_key, 'token': trello_token})
    response_object = json.loads(response.text)
    for card in response_object:
        ids_open[card['desc']] = card['id']

    response = requests.get('{}/lists/{}/cards'.format(trello_url, trello_onhold), params={'fields': 'all', 'key': trello_key, 'token': trello_token})
    response_object = json.loads(response.text)
    for card in response_object:
        ids_onhold[card['desc']] = card['id']

    response = requests.get('{}/lists/{}/cards'.format(trello_url, trello_approved), params={'fields': 'all', 'key': trello_key, 'token': trello_token})
    response_object = json.loads(response.text)
    for card in response_object:
        ids_approved[card['desc']] = card['id']


    # find all relevant PRs
    response = requests.get(github_url, headers=github_header)
    response_object = json.loads(response.text)


    # fetch more PRs if there is more than one page
    page = 1
    while 'next' in response.headers.get('link', ''):
        page += 1
        response = requests.get('{}&page={}'.format(github_url, page), headers=github_header)
        response_object = response_object + json.loads(response.text)


    # for all PRs, sort out the relevant ones and create Trello cards from them
    for pr in response_object:
        # do not include PRs from blacklisted repos
        if any([x in pr['repository']['name'] for x in pr_config.blacklist]):
            continue

        elif 'pull_request' not in pr:
            continue

        else:
            # see if the PR already exists on Trello
            # if they do, check label and move to correct list if changed, else do nothing
            if pr['id'] in ids_open:
                if not pr['labels']:
                    continue

                else:
                    labels = []
                    for label in pr['labels']:
                        labels.append(label['name'])

                    if 'QA OK' in labels:
                        # move to approved, remove from prev list
                        requests.put('{}/cards/{}/idList'.format(trello_url, ids_open[pr['id']], ), params={'value': trello_approved, 'key': trello_key, 'token': trello_token})

                    elif 'ON HOLD' in labels:
                        # move to on hold, remove from prev list
                        requests.put('{}/cards/{}/idList'.format(trello_url, ids_open[pr['id']], ), params={'value': trello_onhold, 'key': trello_key, 'token': trello_token})

                    else:
                        continue


            elif pr['id'] in ids_onhold:
                if not pr['labels']:
                    # move to open, remove from prev board
                    requests.put('{}/cards/{}/idList?'.format(trello_url, ids_onhold[pr['id']], ), params={'value': trello_open, 'key': trello_key, 'token': trello_token})

                else:
                    labels = []
                    for label in pr['labels']:
                        labels.append(label['name'])

                    if 'QA OK' in labels:
                        # move to approved, remove from prev list
                        requests.put('{}/cards/{}/idList'.format(trello_url, ids_onhold[pr['id']], ), params={'value': trello_approved, 'key': trello_key, 'token': trello_token})

                    elif 'ON HOLD' in labels:
                        continue

                    else:
                        # move to open, remove from prev board
                        requests.put('{}/cards/{}/idList?'.format(trello_url, ids_onhold[pr['id']], ), params={'value': trello_open, 'key': trello_key, 'token': trello_token})


            elif pr['id'] in ids_approved:
                if not pr['labels']:
                    # move to open, remove from prev board
                    requests.put('{}/cards/{}/idList'.format(trello_url, ids_approved[pr['id']], ), params={'value': trello_open, 'key': trello_key, 'token': trello_token})
                else:
                    labels = []
                    for label in pr['labels']:
                        labels.append(label['name'])

                    if 'QA OK' in labels:
                        continue

                    elif 'ON HOLD' in labels:
                        # move to on hold, remove from prev board
                        requests.put('{}/cards/{}/idList'.format(trello_url, ids_approved[pr['id']], ), params={'value': trello_onhold, 'key': trello_key, 'token': trello_token})

                    else:
                        # move to open, remove from prev board
                        requests.put('{}/cards/{}/idList'.format(trello_url, ids_approved[pr['id']], ), params={'value': trello_open, 'key': trello_key, 'token': trello_token})

            else:
                # create new card
                # if new PR with no label, create card on open
                if not pr['labels']:
                    payload = {
                        "idList": trello_open,
                        "name": pr['repository']['name'] + ' // ' + pr['title'],
                        "desc": pr['id'],
                        "urlSource": pr['html_url'],
                        "key": trello_key,
                        "token": trello_token
                    }

                    response = requests.post('{}/cards'.format(trello_url), params=payload)

                else:
                    labels = []
                    for label in pr['labels']:
                        labels.append(label['name'])

                    # if new PR with label qa ok, create new card on approved
                    if 'QA OK' in labels:
                        payload = {
                            "idList": trello_approved,
                            "name": pr['repository']['name'] + ' // ' + pr['title'],
                            "desc": pr['id'],
                            "urlSource": pr['html_url'],
                            "key": trello_key,
                            "token": trello_token
                        }

                        response = requests.post('{}/cards'.format(trello_url), params=payload)

                    # if new PR with label dependencies, ignore PR
                    elif 'dependencies' in labels:
                        continue

                    # if new PR with label on hold, create card on on hold
                    elif 'ON HOLD' in labels:
                        payload = {
                            "idList": trello_onhold,
                            "name": pr['repository']['name'] + ' // ' + pr['title'],
                            "desc": pr['id'],
                            "urlSource": pr['html_url'],
                            "key": trello_key,
                            "token": trello_token
                        }

                        response = requests.post('{}/cards'.format(trello_url), params=payload)

                    # if new PR with any other label, create card on open
                    else:
                        payload = {
                            "idList": trello_open,
                            "name": pr['repository']['name'] + ' // ' + pr['title'],
                            "desc": pr['id'],
                            "urlSource": pr['html_url'],
                            "key": trello_key,
                            "token": trello_token
                        }

                        response = requests.post('{}/cards'.format(trello_url), params=payload)


    # archive card if they have been merged or closed
    git_ids = []
    for git_id in response_object:
        git_ids.append(int(git_id['id']))

    trello_ids = dict(list(ids_open.items()) + list(ids_onhold.items()) + list(ids_approved.items()))

    for id_ in trello_ids:
        if id_ not in git_ids:
            response = requests.put('{}/cards/{}/closed'.format(trello_url, trello_ids[id_]), params={'value': 'true', 'key': trello_key, 'token': trello_token})

if __name__ == '__main__':
    main()
