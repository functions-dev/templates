/**
 * Your Node function! This is a template function that simply prints 
 * 'Hello, World!' to the caller, and returns an error if the incoming request
 * is something other than an HTTP POST or GET.
 *
 * In can be invoked with 'func invoke'
 * It can be tested with 'npm test'
 *
 * @param {Context} context a context object.
 * @param {object} context.body the request body if any
 * @param {object} context.query the query string deserialized as an object, if any
 * @param {object} context.log logging object with methods for 'info', 'warn', 'error', etc.
 * @param {object} context.headers the HTTP request headers
 * @param {string} context.method the HTTP request method
 * @param {string} context.httpVersion the HTTP protocol version
 * See: https://github.com/knative/func/blob/main/docs/function-developers/nodejs.md#the-context-object
 */
const handle = async (context, body) => {
  console.log("Recieved request!") // printed on server
  // If the request is an HTTP GET/POST
  if (context.method === 'POST' || context.method === 'GET'){
    return { statusMessage: "Hello Node World!"} // send to client
  } else {
    return { statusCode: 405, statusMessage: 'Method not allowed' };
  }
}

// Export the function
module.exports = { handle };
