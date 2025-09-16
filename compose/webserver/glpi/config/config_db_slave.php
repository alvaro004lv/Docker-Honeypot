<?php 
 class DBSlave extends DBmysql { 
 public $slave = true; 
 public $dbhost = 'localhost';
 public $dbuser = 'glpi'; 
 public $dbpassword= 'glpi'; 
 public $dbdefault = 'glpi'; 
 }
define('DEBUG_SQL', true);
