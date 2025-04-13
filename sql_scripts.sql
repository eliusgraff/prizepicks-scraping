--procedure to remove rows from a table which contain duplicate value in same column
DROP PROCEDURE IF EXISTS REMOVE_DUPES;
DELIMITER ;;
CREATE PROCEDURE REMOVE_DUPES()
BEGIN
    DELETE t1
        FROM table_name AS t1 -- Replace table_name with target table to run procedure on
        INNER JOIN table_name AS t2
        ON t1.column_name = t2.column_name -- Replace column_name with name of actual column to remove copies of
        WHERE t1.id < t2.id  -- Replace 'id' with your primary key or a unique identifier
END;
;;
DELIMITER ;

--Procedure to add parsenums to a table that needs them but doesnt have them just be looking at the time it was parsed
DROP PROCEDURE IF EXISTS ADD_PARSENUMS;
DELIMITER ;;
CREATE PROCEDURE ADD_PARSENUMS()
BEGIN
    DECLARE n INT DEFAULT 0;
    DECLARE i INT DEFAULT 0;
    DECLARE my_key INT DEFAULT 0;
    DECLARE dt DATETIME DEFAULT null;
    SELECT COUNT(*) FROM dev_scrape_data INTO n;
    SET i = 0;
    WHILE i<n DO
        SELECT store_time FROM dev_scrape_data LIMIT i,1 INTO dt;
        SELECT id FROM dev_scrape_data WHERE store_time = dt LIMIT 1 INTO my_key;
        UPDATE dev_proj_ts SET parsenum = my_key WHERE my_time = dt;
        SET i = i+1;
    END WHILE;
END;
;;
DELIMITER ;

SET SQL_SAFE_UPDATES = 0;
CALL ADD_PARSENUMS();
SET SQL_SAFE_UPDATES = 1;