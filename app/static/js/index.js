;(function(){

    url = 'http://127.0.0.1:5000/v1'

  /**
    * ****************************************************
    *  DOMの構築が完了してから実行する
    * ****************************************************
    */

  $(function() {

    var app = new Vue({
        delimiters: ['${', '}'],
        el: '#spam-result',
        data: {
            probability: '',
            vocabulary: ''
        }
    })

    $("#spam_api_send_button").click(function(){

        NProgress.start();

        app.probability = '';
        app.vocabulary = '';

        const spam_button = $(this)
        spam_button.addClass('disabled');

        axios.post(url + '/spams', {
            body: $('#textarea_spam_body').val()
        })
        .then(function (response) {
            // 自動でjsonをjsオブジェクトに変換してくれる
            app.probability = response.data.spam.probability;
            app.vocabulary = response.data.spam.vocabulary;

            spam_button.removeClass('disabled');

            spam_button.addClass('hide');
            $('#spam_feedback_box').removeClass('hide');

            NProgress.done();
        })
        .catch(function (error) {
          alert(error.response.status + '  ' + error.response.data.message);
        });

    });

    $(".spam_feedback_button").click(function(){
        $('#spam_api_send_button').removeClass('hide');
        $('#spam_feedback_box').addClass('hide');
    });


  });
})();
