package functions;

import java.net.URI;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.RequestEntity;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.*;

@SpringBootTest(classes = CloudFunctionApplication.class,
  webEnvironment = WebEnvironment.RANDOM_PORT)
public class EchoCaseFunctionTest {

  @Autowired
  private TestRestTemplate rest;

  @Test
  public void testEcho() throws Exception {
    URI uri = new URI("/");

     // Create RequestEntity with body and headers
    HttpHeaders headers = new HttpHeaders();
    headers.add("Content-Type", "application/json"); // Add headers if needed, like content type
    RequestEntity<String> request = new RequestEntity<>("{}", headers, HttpMethod.POST, uri);
    // Send POST req and get response
    ResponseEntity<String> response = this.rest.exchange(request,String.class);
    // assert status code and return value
    assertThat(response.getStatusCode().value(), equalTo(200));
    assertThat(response.getBody(), containsString("{\"message\":\"Hello Springboot World!\"}"));
  }
}
