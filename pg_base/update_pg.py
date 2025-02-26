from pg_base.connection_pg import update_data


def update_order_by_id(schema, order_id, status_id, body_json, platform_uid):
    body_json = f", body_json='{body_json}'::JSONB" if body_json else ''
    platform_uid = f', platform_uid={platform_uid}' if platform_uid else ''

    update_text = f'''-- Обновим ордер:
    UPDATE "{schema}".orders
	SET status_id={status_id} 
	{body_json}
	{platform_uid}
	WHERE order_id={order_id}
	;'''

    return update_data(update_text)
