-- MySQL dump 10.13  Distrib 8.0.42, for Linux (x86_64)
--
-- Host: localhost    Database: pp_dev
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `game`
--

DROP TABLE IF EXISTS `game`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `game` (
  `id` int NOT NULL,
  `external_game_id` varchar(64) DEFAULT NULL,
  `away` varchar(64) DEFAULT NULL,
  `home` varchar(64) DEFAULT NULL,
  `status` varchar(32) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `game_change_history`
--

DROP TABLE IF EXISTS `game_change_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `game_change_history` (
  `game_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `game_timeseries`
--

DROP TABLE IF EXISTS `game_timeseries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `game_timeseries` (
  `game_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `league`
--

DROP TABLE IF EXISTS `league`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `league` (
  `id` int NOT NULL,
  `icon` varchar(64) DEFAULT NULL,
  `league_icon_id` int DEFAULT NULL,
  `name` varchar(16) DEFAULT NULL,
  `projections_count` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `league_change_history`
--

DROP TABLE IF EXISTS `league_change_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `league_change_history` (
  `league_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL,
  PRIMARY KEY (`league_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `league_timeseries`
--

DROP TABLE IF EXISTS `league_timeseries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `league_timeseries` (
  `league_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL,
  PRIMARY KEY (`league_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `new_player`
--

DROP TABLE IF EXISTS `new_player`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `new_player` (
  `id` int NOT NULL,
  `name` varchar(64) DEFAULT NULL,
  `position` varchar(10) DEFAULT NULL,
  `display_name` varchar(64) DEFAULT NULL,
  `combo` tinyint DEFAULT '0',
  `league_id` int DEFAULT NULL,
  `team_id` varchar(8) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `new_player_change_history`
--

DROP TABLE IF EXISTS `new_player_change_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `new_player_change_history` (
  `new_player_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL,
  PRIMARY KEY (`new_player_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `new_player_timeseries`
--

DROP TABLE IF EXISTS `new_player_timeseries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `new_player_timeseries` (
  `new_player_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL,
  PRIMARY KEY (`new_player_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projection`
--

DROP TABLE IF EXISTS `projection`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `projection` (
  `my_type` varchar(20) NOT NULL,
  `id` varchar(16) NOT NULL,
  `adjusted_odds` tinyint DEFAULT NULL,
  `my_description` varchar(45) NOT NULL,
  `discount_name` varchar(45) DEFAULT NULL,
  `discount_percentage` float DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `flash_sale_line_score` varchar(45) DEFAULT NULL,
  `game_id` varchar(45) DEFAULT NULL,
  `is_promo` tinyint DEFAULT NULL,
  `odds_type` varchar(45) DEFAULT NULL,
  `projection_type` varchar(45) DEFAULT NULL,
  `refundable` tinyint DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `stat_type` varchar(45) DEFAULT NULL,
  `duration` varchar(90) DEFAULT NULL,
  `league` varchar(90) DEFAULT NULL,
  `new_player` varchar(90) DEFAULT NULL,
  `projection_type_id` varchar(10) DEFAULT NULL,
  `score` varchar(90) DEFAULT NULL,
  `stat_type_id` varchar(10) DEFAULT NULL,
  `game` varchar(16) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `league_index` (`league`),
  KEY `player_index` (`new_player`),
  KEY `stat_index` (`stat_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projection_change_history`
--

DROP TABLE IF EXISTS `projection_change_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `projection_change_history` (
  `projection_id` varchar(20) NOT NULL,
  `colname` varchar(32) NOT NULL,
  `newvalue` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL,
  KEY `id_index` (`projection_id`),
  KEY `parse_index` (`parsenum`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projection_timeseries`
--

DROP TABLE IF EXISTS `projection_timeseries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `projection_timeseries` (
  `projection_id` int NOT NULL,
  `name` varchar(45) DEFAULT NULL,
  `val` float NOT NULL,
  `parsenum` int DEFAULT NULL,
  KEY `id_index` (`projection_id`),
  KEY `parse_index` (`parsenum`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projection_type`
--

DROP TABLE IF EXISTS `projection_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `projection_type` (
  `id` int NOT NULL,
  `name` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projection_type_change_history`
--

DROP TABLE IF EXISTS `projection_type_change_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `projection_type_change_history` (
  `projection_type_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projection_type_timeseries`
--

DROP TABLE IF EXISTS `projection_type_timeseries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `projection_type_timeseries` (
  `projection_type_id` int NOT NULL,
  `name` varchar(45) DEFAULT NULL,
  `val` varchar(45) DEFAULT NULL,
  `parsenum` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `scrape_data`
--

DROP TABLE IF EXISTS `scrape_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `scrape_data` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `my_status` int NOT NULL DEFAULT '1',
  `league_num` tinyint unsigned NOT NULL,
  `store_time` datetime DEFAULT NULL,
  `is_cleaned` tinyint NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `league_index` (`league_num`),
  KEY `time_index` (`store_time`)
) ENGINE=InnoDB AUTO_INCREMENT=10516 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stat_type`
--

DROP TABLE IF EXISTS `stat_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stat_type` (
  `id` int NOT NULL,
  `name` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stat_type_change_history`
--

DROP TABLE IF EXISTS `stat_type_change_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stat_type_change_history` (
  `stat_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL,
  PRIMARY KEY (`stat_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stat_type_timeseries`
--

DROP TABLE IF EXISTS `stat_type_timeseries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stat_type_timeseries` (
  `stat_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL,
  PRIMARY KEY (`stat_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `team`
--

DROP TABLE IF EXISTS `team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `team` (
  `id` int NOT NULL,
  `abbreviation` varchar(32) DEFAULT NULL,
  `name` varchar(45) DEFAULT NULL,
  `market` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `team_change_history`
--

DROP TABLE IF EXISTS `team_change_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `team_change_history` (
  `team_id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `val` varchar(64) DEFAULT NULL,
  `parsenum` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `team_timeseries`
--

DROP TABLE IF EXISTS `team_timeseries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `team_timeseries` (
  `team_id` int NOT NULL,
  `name` varchar(45) DEFAULT NULL,
  `val` varchar(45) DEFAULT NULL,
  `parsenum` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-22 20:31:15
