-- KPIs globales
CREATE OR REPLACE VIEW vw_kpi_globales AS
SELECT
  COUNT(*)                                                        AS total_reservas,
  COUNT(*) FILTER (WHERE booking_status = 'Completed')            AS completadas,
  COUNT(*) FILTER (WHERE booking_status = 'Cancelled by Customer') AS canc_cliente,
  COUNT(*) FILTER (WHERE booking_status = 'Cancelled by Driver')   AS canc_conductor,
  COUNT(*) FILTER (WHERE booking_status IN ('Incomplete','No Driver Found')) AS incidencias,
  ROUND(100.0*COUNT(*) FILTER (WHERE booking_status='Completed')/COUNT(*),2)             AS pct_exito,
  ROUND(100.0*COUNT(*) FILTER (WHERE booking_status='Cancelled by Customer')/COUNT(*),2) AS pct_canc_cliente,
  ROUND(100.0*COUNT(*) FILTER (WHERE booking_status='Cancelled by Driver')/COUNT(*),2)   AS pct_canc_conductor,
  ROUND(100.0*COUNT(*) FILTER (WHERE booking_status IN ('Cancelled by Customer','Cancelled by Driver'))/COUNT(*),2) AS pct_canc_directa,
  ROUND(100.0*COUNT(*) FILTER (WHERE booking_status IN ('Incomplete','No Driver Found'))/COUNT(*),2) AS pct_incidencias
FROM fact_bookings;

-- P1: cancelación y pérdida estimada por vehículo y línea de negocio
CREATE OR REPLACE VIEW vw_p1_cancelacion_vehiculo AS
SELECT
  v.business_line,
  v.vehicle_type,
  COUNT(*)                                                        AS reservas,
  COUNT(*) FILTER (WHERE f.booking_status IN ('Cancelled by Customer','Cancelled by Driver')) AS cancelaciones,
  ROUND(100.0*COUNT(*) FILTER (WHERE f.booking_status IN ('Cancelled by Customer','Cancelled by Driver'))/COUNT(*),2) AS tasa_cancelacion_pct,
  ROUND(SUM(f.booking_value) FILTER (WHERE f.booking_status <> 'Completed'),2) AS perdida_estimada_inr
FROM fact_bookings f
JOIN dim_vehiculo v ON v.vehicle_sk = f.vehicle_sk
GROUP BY v.business_line, v.vehicle_type;

-- P2: tiempo de llegada (Avg_VTAT) vs. cancelación
CREATE OR REPLACE VIEW vw_p2_vtat_cancelacion AS
SELECT
  CASE WHEN f.avg_vtat IS NULL THEN 'Sin dato'
       WHEN f.avg_vtat < 5  THEN '0-5 min'
       WHEN f.avg_vtat < 10 THEN '5-10 min'
       WHEN f.avg_vtat < 15 THEN '10-15 min'
       WHEN f.avg_vtat < 20 THEN '15-20 min'
       ELSE '20+ min' END                                         AS rango_vtat,
  COUNT(*)                                                        AS reservas,
  COUNT(*) FILTER (WHERE f.booking_status = 'Cancelled by Customer') AS canc_cliente,
  ROUND(100.0*COUNT(*) FILTER (WHERE f.booking_status = 'Cancelled by Customer')/COUNT(*),2) AS pct_canc_cliente,
  ROUND(AVG(f.avg_vtat)::numeric,2)                               AS vtat_promedio
FROM fact_bookings f
GROUP BY 1;

-- P3: franja horaria, día y método de pago
CREATE OR REPLACE VIEW vw_p3_cancelacion_tiempo AS
SELECT t.franja_horaria, t.dia_semana,
       COUNT(*) AS reservas,
       COUNT(*) FILTER (WHERE f.booking_status IN ('Cancelled by Customer','Cancelled by Driver')) AS cancelaciones
FROM fact_bookings f
JOIN dim_tiempo t ON t.time_sk = f.time_sk
GROUP BY t.franja_horaria, t.dia_semana;

CREATE OR REPLACE VIEW vw_p3_cancelacion_pago AS
SELECT p.payment_method,
       COUNT(*) AS reservas,
       COUNT(*) FILTER (WHERE f.booking_status IN ('Cancelled by Customer','Cancelled by Driver')) AS cancelaciones
FROM fact_bookings f
JOIN dim_metodopago p ON p.payment_sk = f.payment_sk
GROUP BY p.payment_method;

CREATE OR REPLACE VIEW vw_p3_causales AS
SELECT c.cancelled_by, c.cancellation_reason, COUNT(*) AS casos
FROM fact_bookings f
JOIN dim_cancelacion c ON c.cancellation_sk = f.cancellation_sk
WHERE c.cancellation_sk <> 0
GROUP BY c.cancelled_by, c.cancellation_reason;