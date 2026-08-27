# ----------------- GUEST LIST & TASK TESTS ----------------- #

def test_create_anonymous_list(client):
    """Test creating a list without logging in returns a UUID and title."""
    response = client.post('/api/lists', json={'title': 'Guest List'})
    assert response.status_code == 201
    data = response.get_json()
    assert 'list_id' in data
    assert data['title'] == 'Guest List'
    assert len(data['list_id']) == 36  # Valid UUID check


def test_add_task_to_list(client):
    """Test adding a task with priority and due date to a list."""
    list_res = client.post('/api/lists', json={'title': 'Project Plan'})
    list_id = list_res.get_json()['list_id']

    task_payload = {
        'description': 'Finish portfolio draft',
        'priority': 'High',
        'due_date': '2026-09-01'
    }
    task_res = client.post(f'/api/lists/{list_id}/tasks', json=task_payload)
    assert task_res.status_code == 201
    task_data = task_res.get_json()
    assert task_data['description'] == 'Finish portfolio draft'
    assert task_data['priority'] == 'High'
    assert task_data['is_completed'] is False


def test_add_empty_task_fails(client):
    """Test that submitting an empty task description returns a 400 error."""
    list_res = client.post('/api/lists', json={'title': 'Notes'})
    list_id = list_res.get_json()['list_id']

    task_res = client.post(f'/api/lists/{list_id}/tasks', json={'description': '   '})
    assert task_res.status_code == 400
    assert 'Description is required' in task_res.get_json()['error']


def test_toggle_task_status(client):
    """Test marking a task as complete via PATCH."""
    list_id = client.post('/api/lists').get_json()['list_id']
    task_id = client.post(f'/api/lists/{list_id}/tasks', json={'description': 'Check emails'}).get_json()['id']

    patch_res = client.patch(f'/api/tasks/{task_id}', json={'is_completed': True})
    assert patch_res.status_code == 200
    assert patch_res.get_json()['is_completed'] is True


def test_delete_task(client):
    """Test removing a task by ID."""
    list_id = client.post('/api/lists').get_json()['list_id']
    task_id = client.post(f'/api/lists/{list_id}/tasks', json={'description': 'Temporary task'}).get_json()['id']

    del_res = client.delete(f'/api/tasks/{task_id}')
    assert del_res.status_code == 204

    # Verify task list is now empty
    get_res = client.get(f'/api/lists/{list_id}')
    assert len(get_res.get_json()['tasks']) == 0


def test_clear_completed_tasks(client):
    """Test bulk removal of completed items only."""
    list_id = client.post('/api/lists').get_json()['list_id']

    t1 = client.post(f'/api/lists/{list_id}/tasks', json={'description': 'Done task'}).get_json()['id']
    t2 = client.post(f'/api/lists/{list_id}/tasks', json={'description': 'Pending task'}).get_json()['id']

    # Mark first task complete
    client.patch(f'/api/tasks/{t1}', json={'is_completed': True})

    # Clear completed
    clear_res = client.delete(f'/api/lists/{list_id}/completed')
    assert clear_res.status_code == 204

    # Ensure only pending task remains
    remaining = client.get(f'/api/lists/{list_id}').get_json()['tasks']
    assert len(remaining) == 1
    assert remaining[0]['id'] == t2


# ----------------- AUTHENTICATION TESTS ----------------- #

def test_user_registration_and_redirect(client):
    """Test user registration successfully logs the user in and redirects to dashboard."""
    response = client.post('/register', data={
        'email': 'developer@example.com',
        'password': 'securepassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'My Task Lists' in response.data


def test_login_invalid_credentials(client):
    """Test logging in with bad credentials returns flash error."""
    response = client.post('/login', data={
        'email': 'nonexistent@example.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Invalid email or password' in response.data