 $("#login-button").click(function(event){
    event.preventDefault();
    
    if ($("input[name=email]").val == "" || $("input[name=name]").val()=="" ||
        $("input[name=password]").val()==""){
        $("#create-button").disable(true);
    }
    else{
        $("#create-button").disable(false);
        var $form = $("#loginForm");
        $form.fadeOut(500);
        $('.wrapper').addClass('form-success');
        var formData = $form.serialize();
        $.postForm("/login",formData);
    }
});

$("#create-button").click(function(event){
    event.preventDefault();
    
    if ($("input[name=email]").val == "" || $("input[name=name]").val()=="" ||
        $("input[name=password]").val()==""){
        $("#create-button").disable(true);
    }
    else{
        $("#create-button").disable(false);
        var $form = $("#createUserForm");
        $form.fadeOut(500);
        $('.wrapper').addClass('form-success');
        var formData = $form.serialize();
        $.postForm("/new",formData)
    }
});

jQuery.fn.extend({
    disable: function(state) {
        return this.each(function() {
            this.disabled = state;
        });
    }
});

$("input[name=email]").blur(function(){
    $this = $(this);
    if (!validateForm.validateEmail($this.val()) || $this.val()=="") {
        $("#emailHelp").removeClass("hidden"); 
        $("#create-button").disable(true);
    }
    else {
        $("#emailHelp").addClass("hidden"); 
        $("#create-button").disable(false);
    };
});

$("input[name=name]").blur(function(){
    $this = $(this);
    if (!validateForm.validateName($this.val()) || $this.val()=="") {
        $("#nameHelp").removeClass("hidden");
        $("#create-button").disable(true);
    }
    
    else{
        $("#nameHelp").addClass("hidden");
        $("#create-button").disable(false);
    }
});

$("input[name=password]").blur(function(){
    $this = $(this);
    if (!validateForm.validatePassword($this.val()) || $this.val()=="") {
        $("#passwordHelp").removeClass("hidden");
        $("#create-button").disable(true);
    }
    else {
        $("#passwordHelp").addClass("hidden");
        $("#create-button").disable(false);
    }
});

jQuery.postForm = function(url,formData){
    $.ajax({
        type:"POST",
        url:url,
        dataType:"text",
        data:formData,
        success:function(response){
            window.location.href="/";
        },
        error:function(error){
            console.log("Error:",error);
        }
    });
};

//jQuery.fn.form2Dic = function(){
    //var fields = this.serializeArray();
    //var json={};
    //for (var i=0;i<fields.length;i++){
        //json[fields[i].name] = fields[i].value;
    //}
    //if(json.next) delete json.next;
    //return json;
//}


//obejct for validating form value.
var validateForm = {
    validateName:function(name){
        var re = /^[0-9a-zA-Z_.-]\w{4,20}$/; 
        return re.test(name);
    },

    validateEmail:function(email){
        var re = /^([\w-]+(?:\.[\w-]+)*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,6}(?:\.[a-z]{2})?)$/i;
        return re.test(email);
    },

    validatePassword:function(password){
        var re = /^(?=.*\d)(?=.*[a-z]).{6,100}$/; 
        return re.test(password);
    }
}
