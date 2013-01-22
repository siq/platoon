class TaskController(object):
    struct_mapping = (('task', 'action'), ('failed', 'failed_action'),
        ('completed', 'completed_action'))

    def create(self, request, response, subject, data):
        self._transpose_struct_fields(data)
        session = self.schema.session

        subject = self.model.create(session, **data)
        session.commit()

        self.idler.interrupt()
        response({'id': subject.id})

    def update(self, request, response, subject, data):
        if not data:
            return response({'id': subject.id})

        self._transpose_struct_fields(data)
        session = self.schema.session

        subject.update(session, **data)
        session.commit()

        self.idler.interrupt()
        response({'id': subject.id})

    def _annotate_resource(self, request, model, resource, data):
        for field, attr in self.struct_mapping:
            value = getattr(model, attr)
            if value:
                resource[field] = value.extract_dict(exclude='id action_id')

    def _transpose_struct_fields(self, data):
        for field, attr in self.struct_mapping:
            value = data.pop(field, None)
            if value:
                data[attr] = value
