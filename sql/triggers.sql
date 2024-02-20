-- PROBABLY BETTER TO DO THIS IN IMPORT FUNCTION!!!!!!!!!!

DELIMITER $$

DROP TRIGGER IF EXISTS update_a_personen$$
DROP TRIGGER IF EXISTS insert_a_personen$$
DROP TRIGGER IF EXISTS delete_a_personen$$

CREATE TRIGGER update_a_personen AFTER UPDATE ON persons
FOR EACH ROW
BEGIN
	IF NEW.full_name != OLD.full_name OR NEW.wikidata_id != OLD.wikidata_id THEN
		CALL update_aperson(NEW.id_person, NEW.full_name, NEW.wikidata_id);
	END IF;
END$$
	
CREATE TRIGGER insert_a_personen AFTER INSERT ON persons
FOR EACH ROW
BEGIN
	CALL update_aperson(NEW.id_person, NEW.full_name, NEW.wikidata_id);
END$$
	
CREATE TRIGGER delete_a_personen AFTER DELETE ON persons
FOR EACH ROW
BEGIN
	CALL delete_aperson(OLD.id_person_unique);
END$$

CREATE PROCEDURE update_aperson (pid INT UNSIGNED, fname VARACHAR(200), qid VARCHAR(20))
BEGIN
	IF qid IS NOT NULL
		SELECT id_person_unique INTO @uid FROM a_persons_unique WHERE wikidata_id = qid;
	ELSE
		SELECT id_person_unique INTO @uid FROM a_persons_unique WHERE full_name = fname;
	END IF;
	
	IF @uid IS NULL
		INSERT INTO a_persons_unique (full_name, first_name, last_name, wikidata_id)
			SELECT full_name, first_name, last_name, wikidata_id FROM persons WHERE id_person = pid;
			SELECT LAST_INSERT_ID() INTO @uid;
	END IF;

	UPDATE persons SET id_person_unique = @uid;
END$$

CREATE PROCEDURE delete_aperson (uid INT UNSIGNED)
BEGIN
	SELECT count(*) INTO @num FROM persons WHERE id_person_unique = @uid;
	IF @num = 0 THEN
		DELETE FROM a_persons_unique WHERE id_person_unique = @uid;
	END IF;
END$$
	
DELIMITER ;