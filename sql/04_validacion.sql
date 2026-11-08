-- 1. Conteo (esperado: 148767; origen 150000 = 148767 + 1233 duplicados descartados)
SELECT COUNT(*) AS filas_fact FROM fact_bookings;

-- 2. Cancellation_SK nulos (esperado: 0)
SELECT COUNT(*) AS cancellation_sk_nulos FROM fact_bookings WHERE cancellation_sk IS NULL;

-- 3. FK huérfanas (esperado: 0 en las cuatro)
SELECT
 (SELECT COUNT(*) FROM fact_bookings f LEFT JOIN dim_vehiculo   d ON d.vehicle_sk=f.vehicle_sk           WHERE d.vehicle_sk IS NULL)      AS huerf_vehiculo,
 (SELECT COUNT(*) FROM fact_bookings f LEFT JOIN dim_metodopago d ON d.payment_sk=f.payment_sk           WHERE d.payment_sk IS NULL)      AS huerf_pago,
 (SELECT COUNT(*) FROM fact_bookings f LEFT JOIN dim_cancelacion d ON d.cancellation_sk=f.cancellation_sk WHERE d.cancellation_sk IS NULL) AS huerf_cancel,
 (SELECT COUNT(*) FROM fact_bookings f LEFT JOIN dim_tiempo     d ON d.time_sk=f.time_sk                 WHERE d.time_sk IS NULL)         AS huerf_tiempo;

-- 4. Unicidad de Booking_ID (esperado: 0)
SELECT COUNT(*) - COUNT(DISTINCT booking_id) AS duplicados FROM fact_bookings;

-- 5. KPIs reales
SELECT * FROM vw_kpi_globales;

-- 6. Una consulta por pregunta (capturas para el informe)
SELECT * FROM vw_p1_cancelacion_vehiculo ORDER BY tasa_cancelacion_pct DESC;
SELECT * FROM vw_p2_vtat_cancelacion ORDER BY rango_vtat;
SELECT * FROM vw_p3_cancelacion_tiempo ORDER BY cancelaciones DESC LIMIT 10;
SELECT * FROM vw_p3_cancelacion_pago ORDER BY cancelaciones DESC;
SELECT * FROM vw_p3_causales ORDER BY casos DESC LIMIT 10;

