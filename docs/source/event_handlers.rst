Event Handlers
==============

Ramses supports Nefertari model event handlers. The following documentation describes how to define and connect them.


Writing Event Handlers
----------------------

You can write custom functions inside your ``__init__.py`` file, then add the ``@registry.add`` decorator before the functions that you'd like to turn into CRUD event handlers. Ramses CRUD event handlers has the same API as Nefertari CRUD event handlers. Check Nefertari CRUD Events doc for more details on events API.

Example:

.. code-block:: python

    @registry.add
    def log_changed_fields(event):
        import logging
        logger = logging.getLogger('foo')
        changed = ['{}: {}'.format(name, field.new_value)
                   for name, field in event.fields.items()]
        logger.debug('Changed fields: ' + ', '.join(changed))


Connecting Event Handlers
-------------------------

When you define event handlers in your ``__init__.py`` as described above, you can apply them on per-model basis. If multiple handlers are listed, they are executed in the order in which they are listed. Handlers are defined in the root of JSON schema using ``_event_handlers`` property. This property is an object, keys of which are called "event tags" and values are lists of handler names. Event tags are constructed of two parts: ``<type>_<action>`` whereby:

**type**
    Is either ``before`` or ``after``, depending on when handler should run - before view method call or after respectively.

**action**
    Exact name of Nefertari view method that processes the request (action).

    * **index** - Collection GET
    * **create** - Collection POST
    * **update_many** - Collection PATCH/PUT
    * **delete_many** - Collection DELETE
    * **collection_options** - Collection OPTIONS
    * **show** - Item GET
    * **update** - Item PATCH
    * **replace** - Item PUT
    * **delete** - Item DELETE
    * **item_options** - Item OPTIONS
    * **set** - triggers on all the following actions: ``create``, ``update``, ``replace`` and ``update_many``

E.g. This example connects the ``lowercase`` handler to the ``before_set`` event.

.. code-block:: json

    "_event_handlers": {
        "before_set": ["lowercase"]
    }

The ``lowercase`` handler will run before any of the following requests are processed:

    * Collection POST
    * Item PATCH
    * Item PUT
    * Collection PATCH
    * Collection PUT


We will use the following handler to demonstrate how to connect handlers to events. This handler logs ``request``.

.. code-block:: python

    import logging
    log = logging.getLogger(__name__)

    @registry.add
    def log_request(event):
        log.debug(event.view.request)


Note that ramses authentication system triggers events as well. In particular, ramses authentication views trigger ``before_create`` and ``after_create`` events. When event was triggered by instance or subclass of ramses authentication views, event property ``event.is_auth_view`` will equal to ``True``. This may require additional care when event handlers mutate fields which participate in authentication process.


Before vs After
---------------

``Before`` events should be used to:
    * Transform input
    * Perform validation
    * Apply changes to object that is being affected by the request using the ``event.set_field_value`` method

``After`` events should be used to:
    * Change DB objects which are not affected by the request
    * Perform notifications/logging


Registering Event Handlers
--------------------------

To register event handlers, you can define the ``_event_handlers`` property at the root of your model's JSON schema. For example, if we have a JSON schema for the model ``User`` and we want to log all collection GET requests to the ``User`` model after they were processed (using the ``log_request`` handler), we can register the handler in the JSON schema like this:

.. code-block:: json

    {
        "type": "object",
        "title": "User schema",
        "$schema": "http://json-schema.org/draft-04/schema",
        "_event_handlers": {
            "after_index": ["log_request"]
        },
        ...
    }


Other Things You Can Do
-----------------------

You can update another field's value, for example, increment a counter:

.. code-block:: python

    @registry.add
    def increment_count(event):
        counter = event.instance.counter
        incremented = counter + 1
        event.set_field_value('counter', incremented)


You can update other collections (or filtered collections), for example, mark sub-tasks as completed whenever a task is completed:

.. code-block:: python

    @registry.add
    def mark_subtasks_completed(event):
        if 'task' not in event.fields:
            return

        from nefertari import engine
        completed = event.fields['task'].new_value
        instance = event.instance

        if completed:
            subtask_model = engine.get_document_cls('Subtask')
            subtasks = subtask_model.get_collection(task_id=instance.id)
            subtask_model._update_many(subtasks, {'completed': True})


You can perform more complex queries using ElasticSearch:

.. code-block:: python

    @registry.add
    def mark_subtasks_after_2015_completed(event):
        if 'task' not in event.fields:
            return

        from nefertari import engine
        from nefertari.elasticsearch import ES
        completed = event.fields['task'].new_value
        instance = event.instance

        if completed:
            subtask_model = engine.get_document_cls('Subtask')
            es_query = 'task_id:{} AND created_at:[2015 TO *]'.format(instance.id)
            subtasks_es = ES(subtask_model.__name__).get_collection(_raw_terms=es_query)
            subtasks_db = subtask_model.filter_objects(subtasks_es)
            subtask_model._update_many(subtasks_db, {'completed': True})
