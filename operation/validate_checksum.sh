#!/bin/bash
#-xf

## WHAT:   script to verify the chksums of data-files contined in a chksum_input_file
##         No paramaters needed; run from a cron-job once every day/week

# Date:  2018-06-05

## TODO
# -  
# -
#

scriptpath=$(dirname $(readlink -f $0))


log_file="/var/log/vires/chksum_verification.log"
tmp_mail="/tmp/email.tmp"
USER_EMAIL="christian.schiller@eox.at"
ini_file=$scriptpath"/ftp_mirror_config.ini"
## ini_file='/usr/local/vires/ftp_mirror_and_register/ftp_mirror_config.ini'


chksum_input_file=$(grep chksum_file $ini_file |cut -d '=' -f 2 | sed -e "s/'//g")
encoding=$(grep chksum_encoding $ini_file |cut -d '=' -f 2 | sed -e "s/'//g")
storage=$(grep -e '^data' $ini_file |cut -d '=' -f 2 | sed -e "s/'//g" -e "s/\[//g" -e "s/,//g" -e "s/\]//g")
ext="*[cDTs][dBXh][fLTc]"
dupl_files=$(dirname $log_file)'/duplicate_chksum.txt'
uniq_files=$(dirname $log_file)'/uniq_chksum.txt'


function now(){
    date +%Y%m%dT%H%M%SZ
}


function send_email_1(){
    echo "Subject:  [VirES-DEMPO]: chksum testing report -- " $(hostname -f) -- $(now)  > $tmp_mail
    echo "To: " $USER_EMAIL  >> $tmp_mail
    echo "VirES-DEMPO: chksum testing report -- " $(hostname -f) -- $(now)  >> $tmp_mail
    echo "============================="
    echo $result | sed 's/\ \//\n\//' |awk -F '\n' '{print }'  >> $tmp_mail
    echo ''  >> $tmp_mail

    sendmail $USER_EMAIL  < $tmp_mail
    /bin/rm  $tmp_mail
}


function send_email_2(){
    echo "Subject:  [VirES-DEMPO]: Storage-chksum comparison -- " $(hostname -f) -- $(now)  > $tmp_mail
    echo "To: " $USER_EMAIL  >> $tmp_mail
    echo "VirES-DEMPO: Storage-chksum comparison -- " $(hostname -f) -- $(now)  >> $tmp_mail
    echo "============================="
    echo $diff_result  >> $tmp_mail
    echo ''  >> $tmp_mail

    sendmail $USER_EMAIL  < $tmp_mail
    /bin/rm  $tmp_mail
}


# ensure log-file exists and user vires has write access
if [ ! -f $log_file ]; then
    touch $log_file
    chown vires:vires $log_file
fi


# remove any duplicate chksum entries
cat $chksum_input_file | sort | uniq -d > $dupl_files
cat $chksum_input_file | sort | uniq  > $uniq_files
if [ "$(wc -l $dupl_files | awk '{print $1}')" -gt 0 ]; then
    echo "["$(now)"] -- Duplicate chksum entries found/removed: " $(wc -l $dupl_files) >> $log_file
    /bin/cp  $uniq_files $chksum_input_file
    /bin/rm $dupl_files
    /bin/rm $uniq_files
fi


# run the chksum testing stored in the chksum_input_file
if [ $encoding == 'md5' ]; then
    result=$( nice -n 15 md5sum -wc  $chksum_input_file --quiet 2> /dev/null )
    if [ $? != 0 ]; then
        echo "["$(now)"] -- Validation: Problem found with checksum from the chksum_input_file"  >>  $log_file
        echo $result  | sed 's/\ \//\n\//' |awk -F '\n' '{print }'  >>  $log_file
        send_email_1
    else
        echo "["$(now)"] -- Validation: All chksums of chksum_input_file are OK"  >>  $log_file
    fi

elif [ $encoding == 'sha256' ]; then
    result=$( nice -n 15 sha256sum  -wc  $chksum_input_file --quiet 2> /dev/null )
    if [ $? != 0 ]; then
        echo "["$(now)"] -- Validation: Problem found with checksum from the chksum_input_file"  >>  $log_file
        echo $result | sed 's/\ \//\n\//' |awk -F '\n' '{print }'  >>  $log_file
        send_email_1
    else
        echo "["$(now)"] -- Validation: All chksums of chksum_input_file are OK"  >>  $log_file
    fi
fi




# ensure temporary files are gone
if [ -f /tmp/chk_tmp ]; then /bin/rm /tmp/chk_tmp; fi
if [ -f /tmp/store_tmp ]; then /bin/rm /tmp/store_tmp; fi

## get the filelist from the $chksum_input_file
chkfile_flist=($(cat $chksum_input_file  | awk '{print $2}' | sort ))
for elem in ${chkfile_flist[@]}; do
    echo $elem >> /tmp/chk_tmp
done

## get the fiellist from the storage
store_flist=($(find $storage -name $ext | sort))
for elem in ${store_flist[@]}; do
    echo $elem >> /tmp/store_tmp
done


# compare the filenames in the storage with those found in the chksum_input_file
# report if differnces are found
# a) file exists in storage but not found in chksum_input_file -- this is only reported here
# b) filename exists in chksum_input_file but is not in storage -- this is already/also reported by the above text
diff_result=$(diff -a /tmp/chk_tmp /tmp/store_tmp)
if [ $? -gt 0 ]; then
    echo  "["$(now)"] -- Files found in storage without chksum entry in the chksum_input_file:"  >>  $log_file
    echo $diff_result  >>  $log_file
    send_email_2
else
    echo "["$(now)"] -- Stored files and chksum_input_file match"  >>  $log_file
fi


/bin/rm /tmp/chk_tmp
/bin/rm /tmp/store_tmp





