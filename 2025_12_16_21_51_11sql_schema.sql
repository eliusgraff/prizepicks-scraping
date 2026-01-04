use prizepicks_prod;
SELECT * FROM projection_archive WHERE id IN (SELECT id FROM projection);