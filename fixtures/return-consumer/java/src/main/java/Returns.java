class Returns {
 static String source(boolean choose){if(choose)return "left";return null;}
 static void use(){String assigned=source(true);int chained=source(false).length();}
}