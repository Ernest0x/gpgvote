function addChoice(choice_id, choices_id)
{
  var choice = document.createElement('option');
  var choice_to_add = document.getElementById(choice_id);
  if ((/^\s*$/).test(choice_to_add.value)) return;
  var choices = document.getElementById(choices_id);
  for (i = 0; i < choices.length; i++)
    if (choices.options[i].value == choice_to_add.value) return;
  choice.text = choice_to_add.value;
  choice.value = choice_to_add.value;
  choices.add(choice, null);
}

function removeChoices(choices_id)
{
  var choices = document.getElementById(choices_id);
 
  for (i = choices.length-1; i >= 0; i--)
  {
    if(choices.options[i].selected)
    {
      choices.remove(i);
    }
  }
 
}

function selectChoices(choice_set, choices_id)
{
  var choices = document.getElementById(choices_id);
  for (i = 0; i < choices.length; i++)
  {
     if (choice_set == 'all')
       choices.options[i].selected = true;  
     else if (choice_set == 'none')
       choices.options[i].selected = false;
     else
       choice_set = choice_set.split(';')
       for (choice in choice_set)
	 if (choice == choices.options[i].value)
	   choices.options[i].selected = true;
  }
}

function delconfirm(poll_id)
{
  if (! poll_id) poll_id="";
  var del = confirm("Are you sure you want to delete this poll?");
  if (del == true)
    location.replace("/deletepoll/" + poll_id);
}

function checkChoices(choice_id, max)
{
  var choices = document.getElementsByName("choices"); 
  var checked_choices = 0;
  for (i=0; i < choices.length; i++)
  {
     if (choices[i].checked) checked_choices++;
  }
  
  if (checked_choices > max)
  {
    alert("You cannot vote for more than " + max + " choices");
    var choice = document.getElementById(choice_id);
    choice.checked = false;
  } 
}