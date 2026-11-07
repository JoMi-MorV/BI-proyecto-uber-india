-- ============================================================
-- 02_seed.sql | Registros centinela (ejecutar tras 01_ddl.sql)
-- Idempotente: se puede re-ejecutar sin duplicar.
-- ============================================================

INSERT INTO Dim_Cancelacion (Cancellation_SK, Cancelled_By, Cancellation_Reason) VALUES
    (0, 'N/A - Viaje Completado', 'Viaje Completado Sin Incidencias'),
    (1, 'Sistema / Operación',    'Sin Conductor Asignado'),
    (2, 'Cliente',                'Motivo No Registrado'),
    (3, 'Conductor',              'Motivo No Registrado'),
    (4, 'Sistema / Operación',    'Motivo No Registrado')
ON CONFLICT DO NOTHING;

INSERT INTO Dim_MetodoPago (Payment_SK, Payment_Method) VALUES
    (0, 'N/A / No Especificado')
ON CONFLICT DO NOTHING;

-- Las SK que genere el ETL parten después de los centinelas
SELECT setval(pg_get_serial_sequence('dim_cancelacion','cancellation_sk'), 4, true);
SELECT setval(pg_get_serial_sequence('dim_metodopago','payment_sk'),       1, false);