// Wait for the DOM to be ready
$(function() {
    // Initialize form validation on the registration form.
    // It has the name attribute "registration"
    $("form[name='parameters']").validate({
      // Specify validation rules
      rules: {
        // The key name on the left side is the name attribute
        // of an input field. Validation rules are defined
        // on the right side
        satelite: "required",
        startdate: "required",
        enddate: {
          required: true //,
          // Specify that email should be validated
          // by the built-in "email" rule
          // email: true
        },
        measurepoints: {
          required: true
          // minlength: 5
        }
      },
      // Specify validation error messages
      messages: {
        satelite: "Please enter your firstname",
        lastname: "Please enter the starting date",
        password: {
          required: "Please enter the ending date"
        },
        measurepoints: "Please select a valid Point of Interest file"
      },
      // Make sure the form is submitted to the destination defined
      // in the "action" attribute of the form when valid
      submitHandler: function(form) {
        form.submit();
      }
    });
  });