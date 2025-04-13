-- MySQL dump 10.13  Distrib 8.0.33, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: prizepicks
-- ------------------------------------------------------
-- Server version	8.0.33

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `duration`
--

DROP TABLE IF EXISTS `duration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `duration` (
  `id` int NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `version` int DEFAULT NULL,
  `islatest` tinyint DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `game`
--

DROP TABLE IF EXISTS `game`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `game` (
  `id` int NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `external_game_id` varchar(45) DEFAULT NULL,
  `is_live` tinyint DEFAULT NULL,
  `away` varchar(64) DEFAULT NULL,
  `home` varchar(64) DEFAULT NULL,
  `league_name` varchar(10) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `my_version` int DEFAULT NULL,
  `islatest` tinyint DEFAULT NULL
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
  `active` tinyint NOT NULL,
  `f2p_enabled` tinyint NOT NULL,
  `icon` varchar(64) NOT NULL,
  `image_url` varchar(100) NOT NULL,
  `last_five_games_enabled` tinyint NOT NULL,
  `league_icon_id` int NOT NULL,
  `name` varchar(16) NOT NULL,
  `projections_count` int NOT NULL,
  `rank` int NOT NULL,
  `show_trending` tinyint NOT NULL,
  `is_data` tinyint DEFAULT '0',
  `version` int DEFAULT NULL,
  `islatest` tinyint(1) DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `league_data`
--

DROP TABLE IF EXISTS `league_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `league_data` (
  `league_id` int NOT NULL,
  `time_set` datetime NOT NULL,
  `data` varchar(64) NOT NULL,
  `version` int DEFAULT NULL,
  `islatest` tinyint(1) DEFAULT '1',
  KEY `league_id` (`league_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `lfg_ignored_leagues`
--

DROP TABLE IF EXISTS `lfg_ignored_leagues`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `lfg_ignored_leagues` (
  `id` int NOT NULL,
  `league_num` int NOT NULL,
  `version` int DEFAULT NULL,
  `islatest` tinyint(1) DEFAULT '1'
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
  `name` varchar(45) NOT NULL,
  `position` varchar(10) NOT NULL,
  `image_url` varchar(200) DEFAULT NULL,
  `display_name` varchar(45) DEFAULT NULL,
  `combo` tinyint NOT NULL DEFAULT '0',
  `league_id` int NOT NULL,
  `team_id` varchar(8) NOT NULL,
  `version` int DEFAULT NULL,
  `islatest` tinyint(1) DEFAULT '1'
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
  `board_time` datetime NOT NULL,
  `my_description` varchar(45) NOT NULL,
  `discount_name` varchar(45) DEFAULT NULL,
  `discount_percentage` float DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `flash_sale_line_score` varchar(45) DEFAULT NULL,
  `game_id` varchar(45) DEFAULT NULL,
  `hr_20` tinyint DEFAULT NULL,
  `in_game` tinyint DEFAULT NULL,
  `is_live` tinyint DEFAULT NULL,
  `is_promo` tinyint DEFAULT NULL,
  `odds_type` varchar(45) DEFAULT NULL,
  `projection_type` varchar(45) DEFAULT NULL,
  `my_rank` int DEFAULT NULL,
  `refundable` tinyint DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `stat_type` varchar(45) DEFAULT NULL,
  `my_status` varchar(45) DEFAULT NULL,
  `duration` varchar(90) DEFAULT NULL,
  `league` varchar(90) DEFAULT NULL,
  `new_player` varchar(90) DEFAULT NULL,
  `projection_type_id` varchar(10) DEFAULT NULL,
  `score` varchar(90) DEFAULT NULL,
  `stat_type_id` varchar(10) DEFAULT NULL,
  `game` varchar(16) DEFAULT NULL,
  PRIMARY KEY (`id`)
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
  `my_time` datetime NOT NULL,
  `parsenum` int DEFAULT NULL
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
  `my_time` datetime NOT NULL,
  `parsenum` int DEFAULT NULL
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
  `version` int DEFAULT NULL,
  `islatest` tinyint(1) DEFAULT '1'
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
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=177 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stat_average`
--

DROP TABLE IF EXISTS `stat_average`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stat_average` (
  `id` int NOT NULL,
  `average` float NOT NULL,
  `count` int NOT NULL,
  `version` int NOT NULL,
  `islatest` tinyint NOT NULL DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stat_type`
--

DROP TABLE IF EXISTS `stat_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stat_type` (
  `id` int NOT NULL,
  `lfg_ignored_leagues` int DEFAULT '0',
  `name` varchar(45) NOT NULL,
  `rank` int NOT NULL,
  `version` int NOT NULL DEFAULT '0',
  `islatest` tinyint NOT NULL DEFAULT '1'
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
  `primary_color` varchar(20) DEFAULT NULL,
  `abbreviation` varchar(32) NOT NULL,
  `name` varchar(45) DEFAULT NULL,
  `tertiary_color` varchar(20) DEFAULT NULL,
  `secondary_color` varchar(20) DEFAULT NULL,
  `market` varchar(64) DEFAULT NULL,
  `version` int NOT NULL DEFAULT '0',
  `islatest` tinyint NOT NULL DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `type_cols`
--

DROP TABLE IF EXISTS `type_cols`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `type_cols` (
  `type_name` varchar(16) NOT NULL,
  `col_name` varchar(45) NOT NULL
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

-- Dump completed on 2025-04-12 20:25:59
