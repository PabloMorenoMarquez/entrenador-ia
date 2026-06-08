-- Detalle por serie de cada ejercicio (reps/peso/RIR de cada serie individual).
-- Antes solo se guardaba un agregado por ejercicio (series, reps_realizadas, peso_kg);
-- esta columna permite conservar el desglose serie a serie cuando el usuario lo reporta
-- (p.ej. dropsets o series con peso/reps distintos), evitando perder ese detalle al guardar.

alter table ejercicios_detalle
    add column if not exists series_detalle jsonb;

comment on column ejercicios_detalle.series_detalle is
    'Array opcional [{"numero":1,"reps":10,"peso_kg":80,"rir":2,"nota":""}, ...] con el desglose por serie reportado por el usuario. NULL si solo se dio el agregado.';
