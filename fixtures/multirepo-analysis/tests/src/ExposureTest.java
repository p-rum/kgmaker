class ExposureTest {
  @Test public void checksDecline() {
    given().get("/api/exposure").then().body("decline", equalTo(2));
  }
}
